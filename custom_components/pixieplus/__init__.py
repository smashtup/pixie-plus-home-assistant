"""Pixie Plus — local control of SAL Pixie devices via the gateway (no cloud)."""
from __future__ import annotations

import logging

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_FIRMWARE,
    CONF_GATEWAY,
    CONF_MANUFACTURER,
    CONF_MODEL,
    DOMAIN,
)
from .coordinator import PixieCoordinator

PLATFORMS = [LIGHT_DOMAIN]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pixie Plus from a config entry."""
    coordinator = PixieCoordinator(hass, entry)
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    gateway = entry.data[CONF_GATEWAY]
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"salpixiegateway-{gateway[CONF_DEVICE_ID]}")},
        model=gateway[CONF_MODEL],
        manufacturer=gateway[CONF_MANUFACTURER],
        name=gateway[CONF_DEVICE_NAME],
        sw_version=f"{gateway[CONF_FIRMWARE]}",
    )

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when the gateway IP option changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: PixieCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unloaded
