"""Local gateway coordinator for Pixie Plus.

Replaces the cloud handler: runs one authenticated LAN socket (discover ->
handshake -> heartbeat -> recv), decodes status reports into entity state, and
exposes the same async_on/async_off/async_set_* surface the light platform
calls. Commands are built with the existing command_utils/device tables; the
dimmer set-level uses the captured-and-verified frame from const.ble_level.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .command_utils import (
    make_ble_command_data,
    ble_level,
    ble_color,
    ble_effect,
    ble_cct,
    decode_report,
    decode_broadcast,
)
from .const import (
    PIXIE_DEVICES_SPECS,
    CONF_RGB_LIGHT,
    CONF_CCT_LIGHT,
    CONF_TYPE,
    CONF_STYPE,
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_HOME_ID,
    CONF_HOST,
    CONF_MESHNET,
    CONF_MESHNET2,
    CONF_NETID,
    DOMAIN,
    FLAG_COMMAND,
    FLAG_EACK,
    FLAG_HEARTBEAT,
    HEARTBEAT_SECS,
    RECONNECT_MAX,
    RECONNECT_MIN,
    TCP_PORT
)
from .protocol import (
    decrypt,
    decrypt_payload,
    discover,
    encrypt_frame,
    parse_challenge,
)

_LOGGER = logging.getLogger(__name__)
_ACK = json.dumps({"op": "ack", "code": 0})


class PixieCoordinator(DataUpdateCoordinator):
    """Owns the single authenticated socket; pushes state to entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self._meshnet = entry.data[CONF_MESHNET]
        self._meshnet2 = entry.data[CONF_MESHNET2]
        self._netid = entry.data[CONF_NETID]
        self._host = entry.options.get(CONF_HOST) or entry.data.get(CONF_HOST) or None
        self._devices = entry.data[CONF_DEVICES]
        self._id_to_idx = {d[CONF_DEVICE_ID]: i for i, d in enumerate(self._devices)}
        self._id_to_spec = {
            d[CONF_DEVICE_ID]: PIXIE_DEVICES_SPECS.get(d[CONF_TYPE], {}).get(d[CONF_STYPE], {})
            for d in self._devices
        }

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._session_key: str | None = None
        self._run_task: asyncio.Task | None = None
        self._stopping = False

        self.data = [{"status": None} for _ in self._devices]

    # -- DataUpdateCoordinator: push model, no polling ----------------------

    async def _async_update_data(self):
        # No startup state seed: the cloud onlineList is stale (showed lights on
        # when off) and the local device list carries no usable state. Genuine
        # state comes only from the gateway's own status frames (the broadcast
        # dump on connect + per-device reports), so entities stay unavailable
        # until a real report arrives.
        return self.data

    async def async_start(self) -> None:
        self._stopping = False
        self._run_task = self.hass.loop.create_task(self._run())

    async def async_shutdown(self) -> None:
        self._stopping = True
        if self._run_task:
            self._run_task.cancel()
        await self._close_socket()
        await super().async_shutdown()

    async def _close_socket(self) -> None:
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
        self._reader = self._writer = self._session_key = None

    # -- session loop --------------------------------------------------------

    async def _run(self) -> None:
        backoff = RECONNECT_MIN
        while not self._stopping:
            try:
                if self._host:
                    ip = self._host
                else:
                    ip = await self.hass.async_add_executor_job(
                        discover, self._meshnet, self._meshnet2
                    )
                    if not ip:
                        raise ConnectionError("gateway not found on LAN")
                _LOGGER.info("Pixie gateway at %s; connecting", ip)
                self._reader, self._writer = await asyncio.open_connection(ip, TCP_PORT)
                await self._handshake()
                backoff = RECONNECT_MIN
                hb = self.hass.loop.create_task(self._heartbeat_loop())
                try:
                    await self._read_loop()
                finally:
                    hb.cancel()
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Pixie session error: %s; retry in %ss", err, backoff)
            await self._close_socket()
            if self._stopping:
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, RECONNECT_MAX)

    async def _handshake(self) -> None:
        assert self._reader and self._writer
        chunk = await asyncio.wait_for(self._reader.read(4096), timeout=10)
        b64 = chunk.strip().split(b"\n")[0].decode("utf-8", "ignore")
        data1, data2 = parse_challenge(b64)
        sk = decrypt(data1, str(int(self._netid))).decode("utf-8", "replace")
        verify = decrypt(data2, sk).decode("utf-8", "replace")
        if verify not in (self._meshnet, self._meshnet2):
            raise ConnectionError(f"auth mismatch (verify={verify!r})")
        self._session_key = sk
        await self._send_frame(encrypt_frame(_ACK, sk, FLAG_EACK))
        _LOGGER.info("Pixie gateway authenticated")

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_SECS)
            if self._session_key:
                await self._send_frame(encrypt_frame(_ACK, self._session_key, FLAG_HEARTBEAT))

    async def _read_loop(self) -> None:
        assert self._reader
        buf = b""
        while not self._stopping:
            chunk = await self._reader.read(8192)
            if not chunk:
                raise ConnectionError("gateway closed connection")
            buf += chunk
            # Gateway frames are bare base64 with NO delimiter, and a large frame
            # (e.g. the on-connect broadcast dump) spans multiple TCP segments.
            # Reassemble by structure: a complete frame base64-decodes to 1+16k
            # bytes (flag + AES-CBC blocks) and decrypts to valid JSON.
            frames, buf = self._extract_frames(buf)
            for fr in frames:
                self._handle_frame(fr)
            if len(buf) > 1 << 20:  # runaway guard; drop and resync
                buf = b""

    def _extract_frames(self, buf: bytes) -> tuple[list[bytes], bytes]:
        """Pull all complete frames from the front of buf; return (frames, rest)."""
        frames: list[bytes] = []
        i, n = 0, len(buf)
        while i < n:
            end = i + 4
            found = False
            while end <= n:
                seg = buf[i:end]
                try:
                    raw = base64.b64decode(seg)
                except Exception:  # noqa: BLE001
                    end += 4
                    continue
                if len(raw) >= 17 and (len(raw) - 1) % 16 == 0 and self._frame_ok(seg):
                    frames.append(seg)
                    i = end
                    found = True
                    break
                end += 4
            if not found:
                break  # incomplete frame at the tail; wait for more bytes
        return frames, buf[i:]

    def _frame_ok(self, b64: bytes) -> bool:
        """True if b64 decrypts to valid JSON under the session key."""
        if not self._session_key:
            return False
        try:
            flag, pt = decrypt_payload(b64.decode("utf-8", "ignore"), self._session_key)
            if not pt:
                return flag in (FLAG_EACK, FLAG_HEARTBEAT)
            json.loads(pt.decode("utf-8", "replace"))
            return True
        except Exception:  # noqa: BLE001
            return False

    def _handle_frame(self, b64: bytes) -> None:
        if not b64 or not self._session_key:
            return
        try:
            flag, pt = decrypt_payload(b64.decode("utf-8", "ignore"), self._session_key)
        except Exception:  # noqa: BLE001
            return
        if flag != FLAG_COMMAND or not pt:
            return
        try:
            obj = json.loads(pt.decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            return
        if obj.get("type") != "bleData":
            return
        data_hex = obj.get("data", "")

        # Broadcast dump (sent on connect): genuine state for every device.
        records = decode_broadcast(data_hex)
        if records:
            changed = False
            for dest, level, colour_byte in records:
                if self._apply_status(dest, level, None, colour_byte):
                    changed = True
            if changed:
                self.async_set_updated_data(self.data)
            return

        decoded = decode_report(data_hex)
        if not decoded:
            return
        dest, level, hue, colour_byte = decoded
        if self._apply_status(dest, level, hue, colour_byte):
            self.async_set_updated_data(self.data)

    def _apply_status(self, dest: int, level: int, hue, colour_byte) -> bool:
        """Update one device's cached status. Returns True if it changed.

        hue may be None (broadcast records don't pre-compute it); the colour byte
        is interpreted per device spec (hue*2 for RGB, /127 cct position for CCT).
        """
        idx = self._id_to_idx.get(dest)
        if idx is None:
            return False
        spec = self._id_to_spec.get(dest, {})
        st = self.data[idx]["status"] or {}
        new_status = {"br": level, "hue": st.get("hue", 0), "cct": st.get("cct")}
        if spec.get(CONF_RGB_LIGHT) and colour_byte is not None:
            new_status["hue"] = hue if hue is not None else colour_byte * 2
        elif spec.get(CONF_CCT_LIGHT) and colour_byte is not None:
            new_status["cct"] = min(1.0, colour_byte / 127)
        if st != new_status:
            self.data[idx]["status"] = new_status
            return True
        return False

    # -- sending -------------------------------------------------------------

    async def _send_frame(self, b64: str) -> None:
        if self._writer is None:
            raise ConnectionError("not connected")
        self._writer.write((b64 + "\n").encode())
        await self._writer.drain()

    async def _send_ble(self, ble_hex: str) -> None:
        if not self._session_key:
            raise ConnectionError("no session")
        payload = json.dumps({"to": "ALL", "data": {"data": ble_hex, "type": "bleData"}})
        await self._send_frame(encrypt_frame(payload, self._session_key, FLAG_COMMAND))

    def _set_optimistic(self, device_id: int, br: int) -> None:
        idx = self._id_to_idx.get(device_id)
        if idx is not None:
            st = self.data[idx]["status"] or {}
            self.data[idx]["status"] = {"br": br, "hue": st.get("hue", 0)}
            self.async_set_updated_data(self.data)

    # -- methods called by light.py (handler-compatible surface) ------------

    async def async_on(self, device_type: int, device_stype: int, device_id: int) -> None:
        await self._send_ble(make_ble_command_data(device_type, device_stype, device_id, "on", None))
        self._set_optimistic(device_id, 100)

    async def async_off(self, device_type: int, device_stype: int, device_id: int) -> None:
        await self._send_ble(make_ble_command_data(device_type, device_stype, device_id, "off", None))
        self._set_optimistic(device_id, 0)

    async def async_set_white_brightness(self, device_type: int, device_stype: int,
                                         device_id: int, brightness: int) -> None:
        # brightness is HA 0-255; ble_level wants 0-100 (it scales to 0-255 itself)
        pct = round(brightness * 100 / 255)
        await self._send_ble(ble_level(device_id, pct))
        self._set_optimistic(device_id, pct)

    async def async_set_color(self, device_id: int, r: int, g: int, b: int) -> None:
        await self._send_ble(ble_color(device_id, r, g, b))
        # colour command implies the strip is on; reflect that optimistically
        idx = self._id_to_idx.get(device_id)
        if idx is not None:
            st = self.data[idx]["status"] or {}
            br = st.get("br")
            self.data[idx]["status"] = {
                "br": br if br else 100,
                "hue": st.get("hue", 0),
            }
            self.async_set_updated_data(self.data)

    async def async_set_color_brightness(self, device_id: int, brightness: int) -> None:
        # this strip uses one brightness channel (the dimmer frame) for both
        # white and colour modes
        pct = round(brightness * 100 / 255)
        await self._send_ble(ble_level(device_id, pct))
        self._set_optimistic(device_id, pct)

    async def async_set_effect(self, device_id: int, effect: str, speed: str = "medium") -> None:
        await self._send_ble(ble_effect(device_id, effect, speed))

    async def async_set_color_temp(self, device_id: int, position: float) -> None:
        """position 0.0 (warmest) .. 1.0 (coolest)."""
        await self._send_ble(ble_cct(device_id, position))
        # CCT command implies on; reflect optimistically without clobbering br
        idx = self._id_to_idx.get(device_id)
        if idx is not None:
            st = self.data[idx]["status"] or {}
            br = st.get("br")
            self.data[idx]["status"] = {"br": br if br else 100, "hue": st.get("hue", 0)}
            self.async_set_updated_data(self.data)