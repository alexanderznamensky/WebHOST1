from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Webhost1DataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Webhost1DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([Webhost1RefreshButton(coordinator, entry)])


class Webhost1RefreshButton(CoordinatorEntity[Webhost1DataUpdateCoordinator], ButtonEntity):
    _attr_icon = "mdi:refresh"
    _attr_name = "Обновить данные"

    def __init__(self, coordinator: Webhost1DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        username = self._entry.data["username"]
        self._attr_unique_id = f"webhost1_{username}_refresh"

    @property
    def device_info(self) -> DeviceInfo:
        username = self._entry.data["username"]
        return DeviceInfo(
            identifiers={(DOMAIN, f"webhost1_{username}")},
            name=f"Webhost1 {username}",
            manufacturer="Webhost1",
            model="Hosting Account",
        )

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()