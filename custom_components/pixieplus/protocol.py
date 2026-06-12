"""Crypto and discovery primitives for the Pixie gateway LAN protocol.

Uses the `cryptography` library bundled with Home Assistant — no extra deps.
"""
from __future__ import annotations

import base64
import json
import socket
import time

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .const import UDP_PORT

IV = b"0" * 16  # sixteen 0x30 bytes


def _key(s: str) -> bytes:
    kb = s.encode("utf-8")
    if len(kb) % 16:
        kb += b"\x00" * (16 - len(kb) % 16)
    return kb


def _pad(b: bytes) -> bytes:
    n = 16 - (len(b) % 16)
    return b + bytes([n]) * n


def _unpad(b: bytes) -> bytes:
    if not b:
        return b
    n = b[-1]
    return b[:-n] if 1 <= n <= 16 else b


def decrypt(cipher: bytes, key_str: str) -> bytes:
    d = Cipher(algorithms.AES(_key(key_str)), modes.CBC(IV)).decryptor()
    return _unpad(d.update(cipher) + d.finalize())


def encrypt_frame(plain: str, key_str: str, flag: int) -> str:
    e = Cipher(algorithms.AES(_key(key_str)), modes.CBC(IV)).encryptor()
    ct = e.update(_pad(plain.encode("utf-8"))) + e.finalize()
    return base64.b64encode(bytes([flag]) + ct).decode()


def parse_challenge(b64: str) -> tuple[bytes, bytes]:
    raw = base64.b64decode(b64)
    if raw[0] != 0:
        raise ValueError(f"unexpected challenge flag {raw[0]}")
    return raw[1:17], raw[18:34]


def decrypt_payload(b64: str, key_str: str) -> tuple[int, bytes]:
    raw = base64.b64decode(b64)
    flag, ct = raw[0], raw[1:]
    if len(ct) % 16:
        return flag, b""
    return flag, decrypt(ct, key_str)


def discover(meshnet: str, meshnet2: str, timeout: float = 6.0) -> str | None:
    """Blocking UDP broadcast discovery -> gateway IP, or None.

    Run via hass.async_add_executor_job. Only works on the same subnet; for
    segmented networks set a manual host (CONF_HOST).
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        s.bind(("", UDP_PORT))
        s.settimeout(timeout)
        payload = json.dumps({"type": "user", "data": "request",
                              "MeshNet": meshnet, "MeshNet2": meshnet2})
        s.sendto(payload.encode(), ("255.255.255.255", UDP_PORT))
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = s.recvfrom(4096)
            except socket.timeout:
                break
            try:
                obj = json.loads(data.decode("utf-8", "ignore"))
            except Exception:
                continue
            if obj.get("type") != "GW":
                continue
            mn = {str(obj.get("meshNet", "")), str(obj.get("meshNet2", ""))}
            if meshnet in mn or meshnet2 in mn:
                return addr[0]
        return None
    finally:
        s.close()
