"""Pixie Plus integration."""

import asyncio
import logging

from .pixieplus_handler import PixiePlusHandler

from .const import (
    CONF_GATEWAY,
    DOMAIN,
    CONF_DEVICE_NAME,
    CONF_DEVICE_ID,
    CONF_MODEL,
    CONF_MANUFACTURER,
    CONF_FIRMWARE,
)

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN

# from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
# from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr


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

    device_registry = dr.async_get(hass)
    gateway = entry.data[CONF_GATEWAY]

    _LOGGER.debug("Adding Pixie Gateway (%s)", gateway)

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"salpixiegateway-{gateway[CONF_DEVICE_ID]}")},
        model=gateway[CONF_MODEL],
        manufacturer=gateway[CONF_MANUFACTURER],
        name=gateway[CONF_DEVICE_NAME],
        sw_version=gateway[CONF_FIRMWARE],
    )

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
