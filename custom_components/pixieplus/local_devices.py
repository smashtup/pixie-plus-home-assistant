"""Local device-list fetch from the Pixie gateway (port 53216).

Mirrors the device/gateway dict shape produced by cloud.fetch_homes() so it can
be used as a drop-in, preferred source for the device list — with the cloud as a
fallback. Reuses the AES helpers from protocol.py; stdlib sockets only.

The 53216 exchange:
  client -> "ea" + len(8hex) + nonce(8hex) + base64([0x01] + AES_CBC(req))
  server -> "eb" + len(8hex) + base64(AES_CBC(base64(json)))
key   = utf8("Pixie" + hex(netID XOR unix_second)) zero-padded to 16
nonce = encodes unix_second XOR meshNet2 so the gateway recovers the second
req   = {"get":{"selected":127}}
"""
from __future__ import annotations

import base64
import json
import socket
import time

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_MAC,
    CONF_DEVICE_NAME,
    CONF_FIRMWARE,
    CONF_GATEWAY,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_STYPE,
    CONF_TYPE,
    PIXIE_DEVICES_SPECS,
)

IV = b"0" * 16  # sixteen 0x30 bytes
DL_PORT = 53216
_REQUEST = '{"get":{"selected":127}}'


def _sync_key(unix_s: int, net_id: int) -> bytes:
    xor = int(net_id) ^ int(unix_s)
    combined = "Pixie" + format(xor & 0xFFFFFFFFFFFFFFFF, "x")
    arr = bytearray(16)
    for i, ch in enumerate(combined[:16]):
        arr[i] = ord(ch)
    return bytes(arr)


def _sync_nonce(unix_s: int, mesh_net2: int) -> int:
    m2 = int(mesh_net2)
    nonce_high = ((int(unix_s) >> 24) ^ (m2 >> 24)) & 0xFF
    nonce_low24 = (int(unix_s) & 0xFFFFFF) ^ (m2 & 0xFFFFFF)
    return ((nonce_high << 24) | (nonce_low24 & 0xFFFFFF)) & 0xFFFFFFFF


def _aes_encrypt(plain: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    n = 16 - (len(plain) % 16)
    plain = plain + bytes([n]) * n
    e = Cipher(algorithms.AES(key), modes.CBC(IV)).encryptor()
    return e.update(plain) + e.finalize()


def _aes_decrypt(cipher: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    d = Cipher(algorithms.AES(key), modes.CBC(IV)).decryptor()
    pt = d.update(cipher) + d.finalize()
    if pt and 1 <= pt[-1] <= 16:        # strip PKCS7
        pt = pt[:-pt[-1]]
    return pt


def fetch_devices_local(host: str, meshnet: str, meshnet2: str, netid: str,
                        timeout: float = 8.0) -> dict:
    """Query the gateway's 53216 service and return {gateway, devices} in the
    cloud.fetch_homes() shape. Raises on any failure so callers can fall back.

    Assumes the caller has an authorized session to the gateway (the coordinator
    keeps the 41578 control socket open, which authorizes this client's IP).
    """
    ts = int(time.time())
    key = _sync_key(ts, int(netid))
    payload = base64.b64encode(bytes([0x01]) + _aes_encrypt(_REQUEST.encode(), key)).decode()
    nonce = _sync_nonce(ts, int(meshnet2))
    wire = f"ea{len(payload):08x}{nonce:08x}{payload}".encode()

    sock = socket.create_connection((host, DL_PORT), timeout=timeout)
    try:
        sock.sendall(wire)
        sock.settimeout(timeout)
        buf = b""
        while len(buf) < 10:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        if buf[:2] != b"eb":
            raise ConnectionError(f"unexpected 53216 reply {buf[:16]!r}")
        total = int(buf[2:10], 16)
        body = buf[10:]
        while len(body) < total:
            chunk = sock.recv(8192)
            if not chunk:
                break
            body += chunk
    finally:
        sock.close()

    raw = base64.b64decode(body[:total].decode("ascii", "ignore"))
    ct = raw[len(raw) % 16:]
    obj = None
    for cand in (ts, ts - 1, ts + 1, ts - 2, ts + 2):
        inner = _aes_decrypt(ct, _sync_key(cand, int(netid)))
        try:
            outer = base64.b64decode(
                inner.decode("ascii", "ignore").rstrip("\x00") + "==="
            )
            parsed = json.loads(outer)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(parsed, dict) and parsed.get("result") == "success":
            obj = parsed
            break
    if obj is None:
        raise ConnectionError("could not decrypt 53216 device list")

    return _map_devices(obj.get("data", {}))


def _map_devices(data: dict) -> dict:
    """Map the decoded deviceList into the {gateway, devices} cloud shape."""
    gateway = None
    devices = []
    for d in data.get("deviceList", []):
        t, st = d.get("type"), d.get("stype")
        spec = PIXIE_DEVICES_SPECS.get(t, {}).get(st)
        if spec is None:
            continue
        if t == 1 and st == 2:  # gateway
            gateway = {
                CONF_DEVICE_ID: d.get("id"),
                CONF_DEVICE_NAME: d.get("name") or "Pixie Gateway",
                CONF_MODEL: spec[CONF_MODEL],
                CONF_MANUFACTURER: spec[CONF_MANUFACTURER],
                CONF_FIRMWARE: d.get("version", 0),
            }
            continue
        devices.append({
            CONF_DEVICE_MAC: d.get("mac"),
            CONF_DEVICE_ID: d.get("id"),
            CONF_DEVICE_NAME: d.get("name") or f"Device {d.get('id')}",
            CONF_FIRMWARE: d.get("version", 0),
            CONF_TYPE: t,
            CONF_STYPE: st,
        })
    if gateway is None:
        gateway = {CONF_DEVICE_ID: 254, CONF_DEVICE_NAME: "Pixie Gateway",
                   CONF_MODEL: "Gateway", CONF_MANUFACTURER: "SAL",
                   CONF_FIRMWARE: 0}
    if not devices:
        raise ConnectionError("53216 returned no known devices")
    return {CONF_GATEWAY: gateway, "devices": devices}


def fetch_devices_local_authorized(host: str | None, meshnet: str, meshnet2: str,
                                   netid: str, timeout: float = 8.0) -> dict:
    """Discover (if needed) -> authorize on 41578 -> fetch the 53216 device list.

    Synchronous (run via hass.async_add_executor_job). Returns the
    {gateway, devices} shape, or raises on any failure so the caller can fall
    back to the cloud device list.
    """
    from .protocol import decrypt, discover, encrypt_frame, parse_challenge

    ip = host or discover(meshnet, meshnet2)
    if not ip:
        raise ConnectionError("gateway not found on LAN")

    # 41578 handshake so the gateway authorizes this client's IP
    ctrl = socket.create_connection((ip, 41578), timeout=timeout)
    try:
        ctrl.settimeout(timeout)
        chunk = ctrl.recv(4096)
        b64 = chunk.strip().split(b"\n")[0].decode("utf-8", "ignore")
        data1, data2 = parse_challenge(b64)
        session_key = decrypt(data1, str(int(netid))).decode("utf-8", "replace")
        verify = decrypt(data2, session_key).decode("utf-8", "replace")
        if verify not in (meshnet, meshnet2):
            raise ConnectionError(f"41578 auth mismatch (verify={verify!r})")
        ctrl.sendall(
            (encrypt_frame('{"op":"ack","code":0}', session_key, 2) + "\n").encode()
        )
        # query the device list while the authorized control socket is open
        return fetch_devices_local(ip, meshnet, meshnet2, netid, timeout=timeout)
    finally:
        ctrl.close()
