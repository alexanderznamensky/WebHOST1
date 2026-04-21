from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
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

    entities = []
    for index, order in enumerate(coordinator.data.get("orders", []), start=1):
        entities.append(Webhost1OrderSensor(coordinator, entry, index))

    async_add_entities(entities)


class Webhost1BaseEntity(CoordinatorEntity):
    def __init__(self, coordinator: Webhost1DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        username = self.entry.data["username"]
        return DeviceInfo(
            identifiers={(DOMAIN, f"webhost1_{username}")},
            name=f"Webhost1 {username}",
            manufacturer="Webhost1",
            model="Hosting Account",
        )


class Webhost1OrderSensor(Webhost1BaseEntity, SensorEntity):
    _attr_icon = "mdi:server"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "RUB"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: Webhost1DataUpdateCoordinator, entry: ConfigEntry, index: int) -> None:
        super().__init__(coordinator, entry)
        self.index = index
        username = self.entry.data["username"]
        self._attr_unique_id = f"webhost1_{username}_order_{index}"

    @property
    def _order(self):
        orders = self.coordinator.data.get("orders", [])
        if self.index - 1 < len(orders):
            return orders[self.index - 1]
        return None

    @property
    def name(self):
        order = self._order
        if not order:
            return f"Webhost1 Order {self.index}"
        return f"Webhost1 {order.get('name')}"

    @property
    def available(self):
        return self._order is not None

    @property
    def native_value(self):
        balance = self.coordinator.data.get("balance")
        if balance is None:
            return 0.0

        try:
            return round(float(balance), 2)
        except (ValueError, TypeError):
            return 0.0

    @property
    def extra_state_attributes(self):
        order = self._order
        if not order:
            return {}

        return {
            "provider": "Webhost1",
            "due_date": order.get("due_date"),
            "days_left": order.get("days_left"),
            "message": order.get("message"),
            "IP": order.get("ip"),
            "Order": order.get("order_id"),
            "price": order.get("price"),
            "tariff": order.get("tariff"),
            "status": order.get("status"),
            "server": order.get("server"),
            "type": order.get("type"),
            "vm_id": order.get("vm_id"),
            "autopay": order.get("autopay"),
            "balance": self.coordinator.data.get("balance"),
            "last_update": self.coordinator.data.get("last_update"),
            "execution_seconds": self.coordinator.data.get("execution_seconds"),
        }