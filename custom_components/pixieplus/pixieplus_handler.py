"""PixiePlus handler"""
import logging

import homeassistant.util.dt as dt_util
from datetime import timedelta
from homeassistant.core import HomeAssistant, callback, CALLBACK_TYPE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD
)
from .const import (
    DOMAIN,
    CONF_INSTALLATION_ID,
    CONF_SESSION_TOKEN,
    CONF_USER_OBJECT_ID,
    CONF_CURRENT_HOME_ID,
    CONF_LIVE_GROUP_ID,
    CONF_DEVICES,
    CONF_DEVICE_NAME,
    CONF_DEVICE_MAC,
    CONF_TYPE,
    CONF_STYPE,
    CONF_MODEL,
    CONF_MANUFACTURER,
    CONF_FIRMWARE,
    PIXIE_DEVICES_SPECS)

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
        self._user_object_id = entry.data.get(CONF_USER_OBJECT_ID)
        self._current_home_id = entry.data[CONF_CURRENT_HOME_ID]
        self._live_group_id = entry.data[CONF_LIVE_GROUP_ID]
        self._devices = entry.data[CONF_DEVICES]
        
        self._pixieplus_cloud = PixiePlusCloud(
            self._username, 
            self._password,
            self._installation_id,
            self._user_object_id,
            self._session_token,
            self._current_home_id,
            self._live_group_id
        )

    async def _async_setup(self):
        try:
            await self.hass.async_add_executor_job(self._pixieplus_cloud.login())
            await self.hass.async_create_background_task(self._pixieplus_cloud.connect_ws, self.on_ws_update_message)
        except Exception as e:
            _LOGGER.error('Could not connect to PixiePlus Cloud [%s]', e) 


    async def _async_update_data(self):
        _LOGGER.info('Updating PixiePlus data...')


    def on_ws_update_message(message):
        _LOGGER.info("Received WS update message: %s", message)

    def convert_device_list(self, devices):
        _LOGGER.debug("Convert device list from Cloud Data to internal representation")
        return {}
    
    def convert_ws_device_list(self, devices):
        _LOGGER.debug("Convert device list from WS Data to internal representation")
        return {}

    async def async_on(self, device_id: int):
        #await self._async_add_command_to_queue('on', {'dest': device_id})
        _LOGGER.debug("Turning on device with device_id: %d", device_id)

    async def async_off(self, device_id: int, _attempt: int = 0):
        #await self._async_add_command_to_queue('off', {'dest': device_id})
        _LOGGER.debug("Turning off device with device_id: %d", device_id)

    async def async_set_color(self, device_id: int, r: int, g: int, b: int, _attempt: int = 0):
        #await self._async_add_command_to_queue('setColor', {'red': r, 'green': g, 'blue': b, 'dest': device_id})
        _LOGGER.debug("Setting color R:%d G:%d B:%d on device with device_id: %d", r, g, b, device_id)

    async def async_set_color_brightness(self, device_id: int, brightness: int, _attempt: int = 0):
        #await self._async_add_command_to_queue('setColorBrightness', {'brightness': brightness, 'dest': device_id})
        _LOGGER.debug("Setting color brightness %d on device with device_id: %d", brightness, device_id)

    async def async_set_white_brightness(self, device_id: int, brightness: int, _attempt: int = 0):
        #await self._async_add_command_to_queue('setWhiteBrightness', {'brightness': brightness, 'dest': device_id})
        _LOGGER.debug("Setting white brightness %d on device with device_id: %d", brightness, device_id)

    async def async_set_effect(self, device_id: int, effect: str, _attempt: int = 0):
        #await self._async_add_command_to_queue('setEffect', {'effect': effect, 'dest': device_id})
        _LOGGER.debug("Setting effect %s on device with device_id: %d", effect, device_id)