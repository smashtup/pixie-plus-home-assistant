"""Config flow for Pixie Plus integration."""

from typing import Mapping, Optional
import logging

import voluptuous as vol

from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.config_entries import ConfigFlow, CONN_CLASS_CLOUD_PUSH
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from .const import (
    DOMAIN,
    CONF_DEVICES,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_MAC,
    CONF_TYPE,
    CONF_STYPE,
    CONF_MODEL,
    CONF_MANUFACTURER,
    CONF_FIRMWARE,
    PIXIE_DEVICES_SPECS,
)

from .pixieplus_cloud import PixiePlusCloud

_LOGGER = logging.getLogger(__name__)


class PixiePlusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Pixie Plus config flow."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_CLOUD_PUSH

    config: Optional[Mapping] = {}

    async def async_step_user(self, user_input: Optional[Mapping] = None):
        errors = {}
        username: str = ""
        password: str = ""
        pixieplus_cloud = None

        if user_input is not None:
            username = user_input.get(CONF_USERNAME, "").lower()
            password = user_input.get(CONF_PASSWORD, "")

        if username and password:
            pixieplus_cloud = PixiePlusCloud(
                get_async_client(self.hass, True), username, password
            )

            try:
                await pixieplus_cloud.login()
            except Exception as e:
                _LOGGER.error("Can not login to Pixie Plus Cloud [%s]", e)
                errors[CONF_PASSWORD] = "cannot_connect"

        if user_input is None or pixieplus_cloud is None or errors:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_USERNAME, default=username): str,
                        vol.Required(CONF_PASSWORD, default=password): str,
                    }
                ),
                errors=errors,
            )

        devices = []
        for device in await pixieplus_cloud.devices():
            _LOGGER.debug("Processing device - %s", device)
            if CONF_DEVICE_ID not in device:
                _LOGGER.warning("Skipped device, missing id - %s", device)
                continue
            if CONF_TYPE not in device:
                _LOGGER.warning("Skipped device, missing type - %s", device)
                continue
            if device[CONF_TYPE] not in PIXIE_DEVICES_SPECS:
                _LOGGER.warning("Skipped device, invalid type - %s", device["type"])
                continue
            if CONF_STYPE not in device:
                _LOGGER.warning("Skipped device, missing stype - %s", device)
                continue
            if device[CONF_STYPE] not in PIXIE_DEVICES_SPECS[device[CONF_TYPE]]:
                _LOGGER.warning("Skipped device, invalid stype - %s", device["stype"])
                continue
            if CONF_DEVICE_NAME not in device:
                _LOGGER.warning("Skipped device, missing name - %s", device)
                continue

            if "version" not in device:
                device[CONF_FIRMWARE] = "unknown"

            devices.append(
                {
                    CONF_DEVICE_ID: device[CONF_DEVICE_ID],
                    CONF_DEVICE_NAME: device[CONF_DEVICE_NAME],
                    CONF_DEVICE_MAC: device[CONF_DEVICE_MAC],
                    CONF_TYPE: device[CONF_TYPE],
                    CONF_STYPE: device[CONF_STYPE],
                    CONF_MODEL: PIXIE_DEVICES_SPECS[device[CONF_TYPE]][
                        device[CONF_STYPE]
                    ][CONF_MODEL],
                    CONF_MANUFACTURER: PIXIE_DEVICES_SPECS[device[CONF_TYPE]][
                        device[CONF_STYPE]
                    ][CONF_MANUFACTURER],
                    CONF_FIRMWARE: device["version"],
                }
            )

        if len(devices) == 0:
            return self.async_abort(reason="no_devices_found")

        data = await pixieplus_cloud.credentials()
        data[CONF_DEVICES] = devices

        return self.async_create_entry(title="Pixie Plus Cloud Control", data=data)
