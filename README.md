# Pixie Plus — Local Home Assistant integration

Local control of SAL **Pixie** Bluetooth-mesh devices (switches, dimmers,
fan-lights) through the **Pixie Plus** gateway, with **no ongoing cloud
dependency**. Commands and live state stay on your LAN.

> **Cloud control has been removed.** Earlier versions of this integration
> relayed every command and state update through SAL's Pixie cloud (a Parse
> backend + websocket). That path is gone: the integration now speaks to your
> gateway directly over the local network. The cloud is contacted only briefly
> at setup and once per startup (see below) — never for control.

## How it works

The integration talks to the Pixie gateway directly over your network using the
gateway's encrypted LAN protocol (AES-128-CBC). It discovers the gateway by UDP
broadcast (or a fixed IP you provide), authenticates with your home's mesh
credentials, holds an authenticated socket open with a heartbeat, sends
`bleData` commands, and decodes the gateway's status reports so manual
wall-switch changes show up in Home Assistant.

### What still uses the cloud (and what no longer does)

Removed — these used to require the cloud and are now fully local:

- Sending commands (on/off, brightness) — was a cloud `LiveGroup` write relayed
  to the gateway; now a direct encrypted LAN command.
- Live state updates — was a cloud websocket subscription; now decoded from the
  gateway's own status reports on the local socket.

Still cloud, by necessity — only credential/state reads, never control:

- **Once at setup:** a single sign-in fetches your home's mesh credentials
  (`meshNet` / `meshNet2` / `netID`) and device list. These live only in SAL's
  cloud, so this one bootstrap read is unavoidable.
- **Once per Home Assistant startup:** an optional best-effort read of current
  device state, so entities show the right on/off and brightness immediately
  instead of waiting for the first local report. If it fails, the integration
  carries on locally.


## Install

1. Copy `custom_components/pixieplus/` into your Home Assistant
   `config/custom_components/` directory (or install via HACS as a custom repo).
2. Restart Home Assistant.
3. Settings → Devices & Services → **Add Integration** → **Pixie Plus**.
4. Sign in with your Pixie Plus account (one-time bootstrap). Pick your home if
   you have more than one.

### Upgrading from the cloud version

The integration keeps the same `pixie_plus` domain, so it upgrades in place.
Because the stored configuration changed (mesh credentials instead of cloud
session tokens), **remove the old integration entry and add it again** after
updating. The `websocket-client` dependency is no longer required.

### Multiple VLANs / subnets

UDP broadcast discovery only works when Home Assistant and the gateway share a
subnet. If they're on different VLANs, set the **Gateway IP** field at setup (or
later via the integration's **Configure** screen). Only the TCP control session
(port `41578`) needs a route from HA to the gateway.

## Status

- Switches and dimmer lights: on/off and brightness — confirmed against real
  hardware and verified byte-for-byte against the official app.
- Live state feedback, including manual wall-switch changes.
- Initial state seeded from the cloud at startup, so entities show real
  on/off and brightness immediately (then the local socket takes over).
- Entities report unavailable until genuine state is known (no fake "off").
- Auto-reconnect with backoff if the gateway drops or reboots.

Plugs/outlets, relays, covers, and RGB/CCT are not yet wired into the local
platform (the device tables and transport are in place; they're a small next
step).