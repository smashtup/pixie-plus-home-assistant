"""Platform for light integration."""

from __future__ import annotations

import colorsys
import logging

from .pixieplus_handler import PixiePlusHandler
from typing import Any

from homeassistant.helpers.typing import StateType
from homeassistant.helpers.entity import DeviceInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    LightEntity,
    ColorMode,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.const import (
    CONF_DEVICES,
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
)
from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_MAC,
    CONF_TYPE,
    CONF_STYPE,
    CONF_MODEL,
    CONF_MANUFACTURER,
    CONF_FIRMWARE,
    CONF_GATEWAY,
    CONF_LIGHT_SWITCH,
    CONF_LIGHT_DIMMER,
    CONF_RGB_LIGHT,
    CONF_CCT_LIGHT,
    PIXIE_DEVICES_SPECS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    _LOGGER.debug("entry %s", entry.data[CONF_DEVICES])

    handler = hass.data[DOMAIN][entry.entry_id]
    lights = []
    for index, device in enumerate(entry.data[CONF_DEVICES]):
        device_specs = PIXIE_DEVICES_SPECS[device[CONF_TYPE]][device[CONF_STYPE]]
        # Skip non lights
        if device_specs[CONF_LIGHT_SWITCH] is False:
            continue

        light = PixieLight(
            handler,
            index,
            device[CONF_DEVICE_MAC],
            device[CONF_DEVICE_ID],
            device[CONF_DEVICE_NAME],
            device[CONF_FIRMWARE],
            device[CONF_TYPE],
            device[CONF_STYPE],
            entry.data[CONF_GATEWAY],
        )
        _LOGGER.info(
            "Setup light %s %s %s %d %d %d %s",
            device[CONF_DEVICE_MAC],
            device[CONF_DEVICE_ID],
            device[CONF_DEVICE_NAME],
            device[CONF_FIRMWARE],
            device[CONF_TYPE],
            device[CONF_STYPE],
            entry.data[CONF_GATEWAY],
        )

        lights.append(light)

    async_add_entities(lights)


def convert_value_to_available_range(value, min_from, max_from, min_to, max_to) -> int:
    normalized = (value - min_from) / (max_from - min_from)
    new_value = min(
        round((normalized * (max_to - min_to)) + min_to),
        max_to,
    )
    return max(new_value, min_to)


class PixieLight(CoordinatorEntity, LightEntity):
    """Representation of an Awesome Light."""

    def __init__(
        self,
        coordinator: PixiePlusHandler,
        idx: int,
        mac: str,
        device_id: int,
        name: str,
        firmware: int,
        device_type: int,
        device_stype: int,
        gateway: dict,
    ):
        """Initialize an PixiePlus Light."""
        super().__init__(coordinator)
        self.idx = idx
        self._handler = coordinator
        self._mac = mac
        self._device_id = device_id
        self._gateway = gateway

        self._attr_name = name
        self._attr_unique_id = f"salpixieswitch-{self._device_id}"

        if self._attr_color_mode is None:
            self._attr_color_mode = ColorMode.ONOFF

        self._firmware = firmware
        self._device_type = device_type
        self._device_stype = device_stype
        self._device_specs = PIXIE_DEVICES_SPECS[device_type][device_stype]

        self._state = None
        self._red = None
        self._green = None
        self._blue = None
        self._white_brightness = None
        self._color_brightness = None
        self._color_temp = None

    @property
    def device_info(self) -> DeviceInfo:
        """Get device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            manufacturer=self._device_specs[CONF_MANUFACTURER],
            model=self._device_specs[CONF_MODEL],
            sw_version=f"{self._firmware}",
            via_device=(DOMAIN, f"salpixiegateway-{self._gateway[CONF_DEVICE_ID]}"),
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self._state is None:
            return False
        return True

    @property
    def state(self) -> StateType:
        """Return the state of the entity."""
        if self._state is None:
            return STATE_UNAVAILABLE

        return STATE_ON if self.is_on else STATE_OFF

    @property
    def rgb_color(self):
        """Return color when in color mode"""
        return (self._red, self._green, self._blue)

    @property
    def brightness(self):
        """Return the brightness of the light."""
        if self.color_mode != ColorMode.RGB:
            if self._white_brightness is None:
                return None
            return self._white_brightness

        if self._color_brightness is None:
            return None
        return self._color_brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        return bool(self._state)

    @property
    def supported_color_modes(self) -> set[ColorMode] | None:
        supported_color_modes = set()
        if self._device_specs[CONF_CCT_LIGHT]:
            supported_color_modes.add(ColorMode.COLOR_TEMP)
        if self._device_specs[CONF_RGB_LIGHT]:
            supported_color_modes.add(ColorMode.RGB)
        if len(supported_color_modes) == 0 and self._device_specs[CONF_LIGHT_DIMMER]:
            supported_color_modes.add(ColorMode.BRIGHTNESS)
        if len(supported_color_modes) == 0:
            supported_color_modes.add(ColorMode.ONOFF)
        return supported_color_modes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        status = {}

        _LOGGER.debug("[%s] Turn on %s", self.unique_id, kwargs)

        if ATTR_RGB_COLOR in kwargs:
            rgb = kwargs[ATTR_RGB_COLOR]
            await self._handler.async_set_color(self._device_id, rgb[0], rgb[1], rgb[2])
            status["red"] = rgb[0]
            status["green"] = rgb[1]
            status["blue"] = rgb[2]
            status["state"] = True

        if ATTR_BRIGHTNESS in kwargs:
            status["state"] = True
            if self.color_mode != ColorMode.RGB:
                device_brightness = kwargs[ATTR_BRIGHTNESS]
                await self._handler.async_set_white_brightness(
                    self._device_type,
                    self._device_stype,
                    self._device_id,
                    device_brightness,
                )
                status["white_brightness"] = device_brightness
            else:
                device_brightness = kwargs[ATTR_BRIGHTNESS]
                await self._handler.async_set_color_brightness(
                    self._device_id, device_brightness
                )
                status["color_brightness"] = device_brightness

        if "state" not in status:
            await self._handler.async_on(
                self._device_type, self._device_stype, self._device_id
            )
            status["state"] = True

        self.status_callback(status)

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        _LOGGER.debug("[%s] turn off", self.unique_id)
        await self._handler.async_off(
            self._device_type, self._device_stype, self._device_id
        )
        self.status_callback({"state": False})

    @callback
    def status_callback(self, status) -> None:
        if "state" in status:
            self._state = status["state"]
        if "white_brightness" in status:
            self._white_brightness = status["white_brightness"]
        if "color_brightness" in status:
            self._color_brightness = status["color_brightness"]
        if "red" in status:
            self._red = status["red"]
        if "green" in status:
            self._green = status["green"]
        if "blue" in status:
            self._blue = status["blue"]

        if "color_mode" in status:
            supported_color_modes = self.supported_color_modes
            if status["color_mode"]:
                self._attr_color_mode = ColorMode.RGB
            elif ColorMode.BRIGHTNESS in supported_color_modes:
                self._attr_color_mode = ColorMode.BRIGHTNESS

        _LOGGER.debug(
            "[%s][%s] mode[%s] Status callback: %s",
            self.unique_id,
            self.name,
            self._attr_color_mode,
            status,
        )

        self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        device = self.coordinator.data[self.idx]
        _LOGGER.info("Updating Light Status: %s", device)
        new_status = {}

        if self._device_specs[CONF_RGB_LIGHT]:
            new_status["color_mode"] = True
            hue_val = device["status"]["hue"]
            if hue_val > 360:
                new_status["red"] = 255
                new_status["green"] = 255
                new_status["blue"] = 255
            else:
                rgb_color = colorsys.hsv_to_rgb(hue_val / 360, 1, 1)
                new_status["red"] = rgb_color[0] * 255
                new_status["green"] = rgb_color[1] * 255
                new_status["blue"] = rgb_color[2] * 255

        if self._device_specs[CONF_LIGHT_DIMMER]:
            if self.color_mode != ColorMode.RGB:
                device_brightness = convert_value_to_available_range(
                    device["status"]["br"], 0, 100, 0, 255
                )
                new_status["white_brightness"] = device_brightness
                if device["status"]["br"] > 0:
                    self._attr_color_mode = ColorMode.BRIGHTNESS
            else:
                device_brightness = convert_value_to_available_range(
                    device["status"]["br"], 0, 100, 0, 255
                )
                new_status["color_brightness"] = device_brightness
        else:
            self._attr_color_mode = ColorMode.ONOFF

        if device["status"]["br"] > 0:
            new_status["state"] = True
        else:
            new_status["state"] = False

        self.status_callback(new_status)
