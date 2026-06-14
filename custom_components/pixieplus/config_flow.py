"""Config flow for Pixie Plus (local control)."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_DEVICES, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback

from .cloud import fetch_homes
from .local_devices import fetch_devices_local_authorized
from .const import (
    CONF_GATEWAY,
    CONF_HOME_ID,
    CONF_HOME_NAME,
    CONF_HOST,
    CONF_MESHNET,
    CONF_MESHNET2,
    CONF_NETID,
    DOMAIN,
)


_LOGGER = logging.getLogger(__name__)


class PixiePlusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sign in once to bootstrap mesh credentials, then run locally."""

    VERSION = 1

    def __init__(self) -> None:
        self._homes: list[dict] = []
        self._host: str | None = None
        self._username: str | None = None
        self._password: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._host = user_input.get(CONF_HOST) or None
            try:
                self._homes = await self.hass.async_add_executor_job(
                    fetch_homes, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except ValueError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                self._username = user_input[CONF_USERNAME]
                self._password = user_input[CONF_PASSWORD]
                if len(self._homes) == 1:
                    return await self._create(self._homes[0])
                return await self.async_step_home()

        schema = vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_HOST): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_home(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            home = next(h for h in self._homes if h["home_id"] == user_input[CONF_HOME_ID])
            return await self._create(home)
        choices = {h["home_id"]: h["home_name"] for h in self._homes}
        return self.async_show_form(
            step_id="home", data_schema=vol.Schema({vol.Required(CONF_HOME_ID): vol.In(choices)})
        )

    async def _create(self, home: dict) -> ConfigFlowResult:
        await self.async_set_unique_id(home["home_id"])
        self._abort_if_unique_id_configured()

        # Prefer the device list straight from the gateway (no cloud); fall back
        # to the cloud list we already fetched if the local query fails.
        gateway = home["gateway"]
        devices = home["devices"]
        try:
            local = await self.hass.async_add_executor_job(
                fetch_devices_local_authorized, self._host,
                home["meshnet"], home["meshnet2"], home["netid"],
            )
            gateway = local[CONF_GATEWAY]
            devices = local["devices"]
            _LOGGER.info("Pixie: using local gateway device list (%d devices)", len(devices))
        except Exception as err:  # noqa: BLE001
            _LOGGER.info("Pixie: local device list unavailable (%s); using cloud list", err)

        return self.async_create_entry(
            title=f"Home — {home['home_name']}",
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_HOME_ID: home["home_id"],
                CONF_HOME_NAME: home["home_name"],
                CONF_MESHNET: home["meshnet"],
                CONF_MESHNET2: home["meshnet2"],
                CONF_NETID: home["netid"],
                CONF_HOST: self._host,
                CONF_GATEWAY: gateway,
                CONF_DEVICES: devices,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "PixiePlusOptionsFlow":
        return PixiePlusOptionsFlow()


class PixiePlusOptionsFlow(OptionsFlow):
    """Set/change the gateway IP without re-adding the integration."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            host = user_input.get(CONF_HOST, "").strip()
            return self.async_create_entry(title="", data={CONF_HOST: host or None})
        current = (self.config_entry.options.get(CONF_HOST)
                   or self.config_entry.data.get(CONF_HOST) or "")
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Optional(CONF_HOST, default=current): str}),
        )
