"""Pixie Plus integration."""

import asyncio
import logging

from .pixieplus_handler import PixiePlusHandler

from .const import (
    DOMAIN,
)

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN

# from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
# from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


# PLATFORMS = [COVER_DOMAIN, LIGHT_DOMAIN, SWITCH_DOMAIN]
PLATFORMS = [LIGHT_DOMAIN]

_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    """Set up the Pixie Plus Cover component from configuration.yaml"""

    if DOMAIN not in config:  # in case there is no cover device
        config[DOMAIN] = {}

    hass.data[DOMAIN] = config[DOMAIN]

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pixie Plus via a config (flow) entry."""

    _LOGGER.info("setup config flow entry %s", entry.data)

    handler = PixiePlusHandler(hass, entry)

    # Make `handler` accessible for all platforms
    hass.data[DOMAIN][entry.entry_id] = handler

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await handler.async_config_entry_first_refresh()

    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unload entry %s", entry.entry_id)
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
