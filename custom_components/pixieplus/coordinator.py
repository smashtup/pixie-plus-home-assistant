"""Local gateway coordinator for Pixie Plus.

Replaces the cloud handler: runs one authenticated LAN socket (discover ->
handshake -> heartbeat -> recv), decodes status reports into entity state, and
exposes the same async_on/async_off/async_set_* surface the light platform
calls. Commands are built with the existing command_utils/device tables; the
dimmer set-level uses the captured-and-verified frame from const.ble_level.
"""
from __future__ import annotations

import asyncio
import json
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .cloud import fetch_states
from .command_utils import make_ble_command_data
from .const import (
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
    TCP_PORT,
    ble_level,
    decode_report,
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
        self._username = entry.data.get(CONF_USERNAME)
        self._password = entry.data.get(CONF_PASSWORD)
        self._home_id = entry.data.get(CONF_HOME_ID)
        self._devices = entry.data[CONF_DEVICES]
        self._id_to_idx = {d[CONF_DEVICE_ID]: i for i, d in enumerate(self._devices)}

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._session_key: str | None = None
        self._run_task: asyncio.Task | None = None
        self._stopping = False
        self._seeded = False

        # data[idx]["status"] is None until genuine data arrives (cloud seed,
        # gateway report, or a command we issue); light.py treats None as
        # unavailable. Real data is always a {"br": 0-100, "hue": int} dict.
        self.data = [{"status": None} for _ in self._devices]

    # -- DataUpdateCoordinator: push model, no polling ----------------------

    async def _async_update_data(self):
        # One-time cloud seed so entities show real state at startup, before any
        # local status report arrives. Best-effort; failures fall back to local.
        if not self._seeded and self._username and self._password and self._home_id:
            self._seeded = True
            states = await self.hass.async_add_executor_job(
                fetch_states, self._username, self._password, self._home_id
            )
            for dev_id, st in states.items():
                idx = self._id_to_idx.get(dev_id)
                if idx is not None:
                    self.data[idx]["status"] = {"br": st.get("br", 0), "hue": st.get("hue", 0)}
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
            if b"\n" in buf:
                *frames, buf = buf.split(b"\n")
            else:
                frames, buf = [buf], b""
            for fr in frames:
                self._handle_frame(fr.strip())

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
        decoded = decode_report(obj.get("data", ""))
        if not decoded:
            return
        dest, level, _ = decoded
        idx = self._id_to_idx.get(dest)
        if idx is None:
            return
        st = self.data[idx]["status"]
        if st is None or st.get("br") != level:
            self.data[idx]["status"] = {"br": level, "hue": (st or {}).get("hue", 0)}
            self.async_set_updated_data(self.data)

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
        _LOGGER.debug("set_color not yet implemented for local transport")

    async def async_set_color_brightness(self, device_id: int, brightness: int) -> None:
        _LOGGER.debug("set_color_brightness not yet implemented for local transport")

    async def async_set_effect(self, device_id: int, effect: str) -> None:
        _LOGGER.debug("set_effect not yet implemented for local transport")
