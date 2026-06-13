"""One-time cloud bootstrap for Pixie Plus (Local).

Used only by the config flow to fetch the mesh credentials (meshNet/meshNet2/
netID) and the device list. After setup the integration runs fully locally.
Stdlib-only (urllib) so it adds no requirements.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_MAC,
    CONF_DEVICE_NAME,
    CONF_DEVICES,
    CONF_FIRMWARE,
    CONF_GATEWAY,
    CONF_HOME_ID,
    CONF_HOME_NAME,
    CONF_MANUFACTURER,
    CONF_MESHNET,
    CONF_MESHNET2,
    CONF_MODEL,
    CONF_NETID,
    CONF_STYPE,
    CONF_TYPE,
    PIXIE_DEVICES_SPECS,
)

BASE = "https://www.pixie.app/p0/pixieCloud/"
APP_ID = "6426f04c206c108275ede71b9fd09ac8"
CLIENT_KEY = "35779bd411c751ff87577cd762118dad"


def _headers(session_token: str | None = None) -> dict:
    h = {
        "x-parse-application-id": APP_ID,
        "x-parse-installation-id": str(uuid.uuid4()),
        "x-parse-client-key": CLIENT_KEY,
        "content-type": "application/json",
    }
    if session_token:
        h["x-parse-session-token"] = session_token
    return h


def _post(path: str, headers: dict, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def _find(obj, key):
    if isinstance(obj, dict):
        if key in obj and not isinstance(obj[key], (dict, list)):
            return obj[key]
        for v in obj.values():
            r = _find(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find(v, key)
            if r is not None:
                return r
    return None


def fetch_homes(username: str, password: str) -> list[dict]:
    """Log in and return homes with mesh creds, gateway info, and devices.

    Each home: {home_id, home_name, meshnet, meshnet2, netid, gateway, devices}.
    Devices/gateway use the same keys the light platform consumes; devices with
    unknown type/stype (no spec) are skipped. Raises ValueError on bad login.
    """
    status, auth = _post("login", _headers(),
                         {"username": username, "password": password, "_method": "GET"})
    if status != 200 or "sessionToken" not in auth:
        raise ValueError(auth.get("error", "login failed"))
    token = auth["sessionToken"]

    status, data = _post("classes/Home", _headers(token),
                         {"where": {}, "limit": 100, "_method": "GET"})
    homes = []
    for home in data.get("results", []):
        meshnet = str(_find(home, "meshNet") or "")
        meshnet2 = str(_find(home, "meshNet2") or "")
        netid = str(_find(home, "netID") or _find(home, "netId") or "")
        if not (meshnet and netid):
            continue

        gateway = None
        devices = []
        for d in home.get("deviceList", []):
            t, st = d.get("type"), d.get("stype")
            spec = PIXIE_DEVICES_SPECS.get(t, {}).get(st)
            if spec is None:
                continue
            if t == 1 and st == 2:  # the gateway
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
        homes.append({
            CONF_HOME_ID: home.get("objectId"),
            CONF_HOME_NAME: _find(home, "name") or home.get("objectId"),
            CONF_MESHNET: meshnet,
            CONF_MESHNET2: meshnet2,
            CONF_NETID: netid,
            CONF_GATEWAY: gateway,
            CONF_DEVICES: devices,
        })

    if not homes:
        raise ValueError("no homes with mesh credentials found")
    return homes


def fetch_states(username: str, password: str, home_id: str) -> dict:
    """Return current per-device status for a home: {id: {"br": int, "hue": int}}.

    Reads the Home object's onlineList (same source the cloud handler used).
    Returns {} on any failure so startup seeding is best-effort.
    """
    try:
        status, auth = _post("login", _headers(),
                             {"username": username, "password": password, "_method": "GET"})
        if status != 200 or "sessionToken" not in auth:
            return {}
        token = auth["sessionToken"]
        status, data = _post("classes/Home", _headers(token),
                             {"where": {"objectId": home_id}, "limit": 1, "_method": "GET"})
        results = data.get("results", [])
        if not results:
            return {}
        online = results[0].get("onlineList", {}) or {}
        out = {}
        for k, v in online.items():
            if not isinstance(v, dict):
                continue
            try:
                out[int(k)] = {"br": int(v.get("br", 0)), "hue": int(v.get("hue", 0))}
            except (TypeError, ValueError):
                continue
        return out
    except Exception:  # noqa: BLE001
        return {}
