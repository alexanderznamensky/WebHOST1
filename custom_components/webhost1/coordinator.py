from __future__ import annotations

import json
import html as html_lib
import logging
import re
import time
from datetime import datetime
from typing import Any

import requests

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://webhost1.ru/"
LOGIN_URL = "https://webhost1.ru/login_check"
ORDERS_URL = "https://webhost1.ru/bp/orders"


class InvalidAuth(Exception):
    """Invalid auth."""


def day_word(days: int) -> str:
    days = abs(days)
    if 11 <= days % 100 <= 14:
        return "дней"
    last = days % 10
    if last == 1:
        return "день"
    if 2 <= days % 10 <= 4:
        return "дня"
    return "дней"


def parse_dt(date_str: str | None) -> datetime | None:
    if not date_str:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def calc_days_left(due_date: str | None) -> int | None:
    dt = parse_dt(due_date)
    if not dt:
        return None
    return (dt - datetime.now()).days


def build_message(name: str, due_date: str | None) -> str:
    if not due_date:
        return f"Не удалось определить дату оплаты Webhost1 - {name}"

    days_left = calc_days_left(due_date)
    if days_left is None:
        return f"Не удалось определить дату оплаты Webhost1 - {name}"

    dword = day_word(days_left)

    if days_left == 0:
        return f"Сегодня срок оплаты Webhost1 - {name}!"
    if 0 < days_left <= 5:
        return f"Через {days_left} {dword} нужно оплатить Webhost1 - {name}!"
    if days_left < 0:
        return f"Просрочена оплата Webhost1 - {name}!!!"
    return f"До оплаты Webhost1 - {name} осталось {days_left} {dword}"


def extract_orders_json(html: str) -> list[dict[str, Any]]:
    match = re.search(r":orders='(.*?)'\s*:columns=", html, re.DOTALL)
    if not match:
        raise UpdateFailed("Не найден атрибут :orders на странице заказов")

    raw = html_lib.unescape(match.group(1))

    try:
        return json.loads(raw)
    except json.JSONDecodeError as err:
        raise UpdateFailed(f"Не удалось разобрать JSON заказов: {err}") from err


def extract_balance(html: str) -> str | None:
    match = re.search(
        r"Баланс:.*?([0-9]+(?:[.,][0-9]+)?)\s*₽",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None

    raw_value = match.group(1).replace(",", ".").strip()

    try:
        value = float(raw_value)
    except ValueError:
        return None

    return f"{value:.2f}".replace(".", ",") + " RUB"


def normalize_order(item: dict[str, Any]) -> dict[str, Any]:
    expired_at = None
    if isinstance(item.get("expired_at"), dict):
        expired_at = item["expired_at"].get("date")

    tariff_name = None
    tariff_obj = item.get("tariffObject")
    if isinstance(tariff_obj, dict):
        tariff_name = tariff_obj.get("name")

    due_date = expired_at
    days_left = calc_days_left(due_date)

    return {
        "name": item.get("name"),
        "order_id": item.get("id"),
        "ip": item.get("ip"),
        "price": item.get("price"),
        "due_date": due_date,
        "days_left": days_left,
        "status": item.get("status"),
        "tariff": tariff_name,
        "server": item.get("server"),
        "type": item.get("type"),
        "vm_id": item.get("vm_id"),
        "autopay": item.get("autopay"),
        "message": build_message(item.get("name", "unknown"), due_date),
    }


def fetch_webhost1_data(username: str, password: str) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BASE_URL,
        "Origin": "https://webhost1.ru",
    })

    session.get(BASE_URL, timeout=30)

    payload = {
        "_username": username,
        "_password": password,
        "rememberMe": "false",
        "code": "",
        "callpass_verify": "null",
        "request_repeat": "false",
    }

    login_resp = session.post(
        LOGIN_URL,
        files={k: (None, v) for k, v in payload.items()},
        timeout=30,
    )

    try:
        login_data = login_resp.json()
    except Exception as err:
        raise UpdateFailed(f"Не удалось разобрать ответ логина: {err}") from err

    if login_data.get("status") != "success":
        raise InvalidAuth(login_data.get("text", "invalid_auth"))

    session.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    })

    orders_resp = session.get(ORDERS_URL, timeout=30)
    if orders_resp.status_code != 200:
        raise UpdateFailed(f"Ошибка загрузки заказов: {orders_resp.status_code}")

    html = orders_resp.text
    orders_raw = extract_orders_json(html)
    orders = [normalize_order(item) for item in orders_raw]
    balance = extract_balance(html)

    return {
        "balance": balance,
        "orders": orders,
    }


class Webhost1DataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, update_interval):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=update_interval,
        )
        self.entry = entry

    async def _async_update_data(self) -> dict[str, Any]:
        username = self.entry.data[CONF_USERNAME]
        password = self.entry.options.get(
            CONF_PASSWORD,
            self.entry.data[CONF_PASSWORD],
        )

        started = time.time()

        try:
            data = await self.hass.async_add_executor_job(
                fetch_webhost1_data,
                username,
                password,
            )
            data["last_update"] = dt_util.now().isoformat()
            data["execution_seconds"] = round(time.time() - started, 2)
            return data
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed(f"invalid_auth: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Ошибка обновления данных Webhost1: {err}") from err