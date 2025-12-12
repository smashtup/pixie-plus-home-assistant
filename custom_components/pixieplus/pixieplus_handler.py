"""PixiePlus handler"""

import logging
import ssl

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.httpx_client import get_async_client

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from .const import (
    DOMAIN,
    CONF_INSTALLATION_ID,
    CONF_SESSION_TOKEN,
    CONF_USER_OBJECT_ID,
    CONF_CURRENT_HOME_ID,
    CONF_LIVE_GROUP_ID,
    CONF_DEVICES,
    CONF_DEVICE_ID,
    CMD_ON,
    CMD_OFF,
    CMD_SET_BRIGHTNESS,
)

from .command_utils import make_ble_command_data

from .pixieplus_cloud import PixiePlusCloud

_LOGGER = logging.getLogger(__name__)


class PixiePlusHandler(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """
        Args :
            hass: HomeAssistance core
            entry: The config flow entry for this integration
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
        self._username = entry.data[CONF_USERNAME]
        self._password = entry.data[CONF_PASSWORD]
        self._installation_id = entry.data[CONF_INSTALLATION_ID]
        self._session_token = entry.data[CONF_SESSION_TOKEN]
        self._user_object_id = entry.data[CONF_USER_OBJECT_ID]
        self._current_home_id = entry.data[CONF_CURRENT_HOME_ID]
        self._live_group_id = entry.data[CONF_LIVE_GROUP_ID]
        self._devices = entry.data[CONF_DEVICES]

        self._last_request_time = -1

        self._pixieplus_cloud = PixiePlusCloud(
            get_async_client(self.hass, True),
            self._username,
            self._password,
            self._installation_id,
            self._user_object_id,
            self._session_token,
            self._current_home_id,
            self._live_group_id,
        )

    async def _async_setup(self):
        _LOGGER.info("Subscribing to PixiePlus updates")
        try:
            ssl_context = await self.hass.async_add_executor_job(
                ssl.create_default_context
            )
            await self._pixieplus_cloud.login()
            self.hass.async_add_executor_job(
                self._pixieplus_cloud.connect_ws, ssl_context
            )
            self._pixieplus_cloud.subscribe_home_updates(self._on_home_update_message)
            self._pixieplus_cloud.subscribe_live_group_updates(
                self._on_live_group_update_message
            )
            self._pixieplus_cloud.subscribe_hp_updates(self._on_hp_update_message)

        except Exception as e:
            _LOGGER.error("Could not connect to PixiePlus Cloud [%s]", e)

    def _extract_devices_with_status(self, home_object):
        device_list = home_object.get("deviceList", [])
        online_list = home_object.get("onlineList", {})

        return {
            device["id"]: device | {"status": online_list.get(f"{device['id']}", None)}
            for device in device_list
        }

    def _update_device_list_status(self, home_object):
        device_list_update = self._extract_devices_with_status(home_object)
        for device in self._devices:
            device_update = device_list_update.get(device[CONF_DEVICE_ID], None)
            if device_update is not None:
                device["status"] = device_update.get("status", None)
        return self._devices

    def _device_string(self, device):
        return f"{device['id']}"

    async def _async_update_data(self):
        _LOGGER.info("Updating PixiePlus data")
        home_object = await self._pixieplus_cloud.home_object()
        self._update_device_list_status(home_object)
        return self._devices

    def _on_home_update_message(self, home_object):
        _LOGGER.info(
            "Received Home update message: %s",
            list(map(self._device_string, home_object["deviceList"])),
        )
        self._update_device_list_status(home_object)
        self.async_set_updated_data(self._devices)

    def _on_live_group_update_message(self, live_group_object):
        _LOGGER.info(
            "Received Live Group update message: %s", live_group_object["Request"]
        )

    def _on_hp_update_message(self, hp_object):
        _LOGGER.info("Received Live Group update message: %s", hp_object)

    async def async_on(self, device_type: int, device_stype: int, device_id: int):
        _LOGGER.debug("Turning on device with device_id: %d", device_id)
        ble_data = make_ble_command_data(
            device_type, device_stype, device_id, CMD_ON, None
        )
        self._last_request_time = await self._pixieplus_cloud.send_live_group_request(
            ble_data
        )

    async def async_off(
        self, device_type: int, device_stype: int, device_id: int, _attempt: int = 0
    ):
        _LOGGER.debug("Turning off device with device_id: %d", device_id)
        ble_data = make_ble_command_data(
            device_type, device_stype, device_id, CMD_OFF, None
        )
        self._last_request_time = await self._pixieplus_cloud.send_live_group_request(
            ble_data
        )

    async def async_set_color(
        self, device_id: int, r: int, g: int, b: int, _attempt: int = 0
    ):
        # await self._async_add_command_to_queue('setColor', {'red': r, 'green': g, 'blue': b, 'dest': device_id})
        _LOGGER.debug(
            "Setting color R:%d G:%d B:%d on device with device_id: %d",
            r,
            g,
            b,
            device_id,
        )

    async def async_set_color_brightness(
        self, device_id: int, brightness: int, _attempt: int = 0
    ):
        # await self._async_add_command_to_queue('setColorBrightness', {'brightness': brightness, 'dest': device_id})
        _LOGGER.debug(
            "Setting color brightness %d on device with device_id: %d",
            brightness,
            device_id,
        )

    async def async_set_white_brightness(
        self,
        device_type: int,
        device_stype: int,
        device_id: int,
        brightness: int,
        _attempt: int = 0,
    ):
        # await self._async_add_command_to_queue('setWhiteBrightness', {'brightness': brightness, 'dest': device_id})
        _LOGGER.debug(
            "Setting white brightness %d on device with device_id: %d",
            brightness,
            device_id,
        )
        ble_data = make_ble_command_data(
            device_type,
            device_stype,
            device_id,
            CMD_SET_BRIGHTNESS,
            f"{brightness:02x}",
        )
        self._last_request_time = await self._pixieplus_cloud.send_live_group_request(
            ble_data
        )

    async def async_set_effect(self, device_id: int, effect: str, _attempt: int = 0):
        # await self._async_add_command_to_queue('setEffect', {'effect': effect, 'dest': device_id})
        _LOGGER.debug(
            "Setting effect %s on device with device_id: %d", effect, device_id
        )
