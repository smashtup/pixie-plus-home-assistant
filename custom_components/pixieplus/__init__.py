"""Pixie Plus integration."""

import asyncio
import logging

from .pixieplus_handler import PixiePlusHandler

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD
)
from .const import (
    DOMAIN,
    CONF_INSTALLATION_ID,
    CONF_SESSION_TOKEN,
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

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


PLATFORMS = [COVER_DOMAIN, LIGHT_DOMAIN, SWITCH_DOMAIN]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up the Pixie Plus Cover component from configuration.yaml"""

    if DOMAIN not in config:  # in case there is no cover device
        config[DOMAIN] = {}

    hass.data[DOMAIN] = config[DOMAIN]

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pixie Plus via a config (flow) entry."""

    _LOGGER.info('setup config flow entry %s', entry.data)

    handler = PixiePlusHandler(hass, entry)

    # Make `handler` accessible for all platforms
    hass.data[DOMAIN][entry.entry_id] = handler

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    _LOGGER.info('Unload entry %s', entry.entry_id)
    if entry.entry_id in hass.data[DOMAIN]:
        await hass.data[DOMAIN][entry.entry_id].async_shutdown()

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
