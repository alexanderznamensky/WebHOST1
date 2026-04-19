# WebHOST1 data parser - Интеграция для Home Assistant

Кастомная интеграция для мониторинга заказов, IP-адресов, стоимости и срока оплаты услуг Webhost1 в Home Assistant.

## 🎯 Особенности

- ✅ Настройка через UI (Config Flow)
- ✅ Автоматическое создание сенсоров заказов
- ✅ Русская локализация
- ✅ Безопасное хранение данных
- ✅ Поддержка реконфигурации пароля и интервала обновления

## 📊 Создаваемые сенсоры

После установки создаются сенсоры заказов Webhost1. Для каждого заказа создаётся отдельный сенсор.

В текущей реализации данные заказа включают:

- состояние сенсора — баланс/стоимость в `RUB`
- атрибуты:
  - `due_date` — срок окончания оплаченного периода
  - `days_left` — дней до окончания
  - `message` — служебное сообщение по оплате
  - `IP` — IP-адрес услуги
  - `Order` — ID заказа
  - `price` — стоимость
  - `tariff` — тариф
  - `status` — статус
  - `server` — ID сервера
  - `type` — тип услуги
  - `vm_id` — ID виртуальной машины
  - `autopay` — автопродление

## 📋 Требования

### Home Assistant

- Home Assistant 2026.x или выше
- Установленная кастомная интеграция в `/config/custom_components/webhost1/`

### Python / зависимости

- `requests`

## 🚀 Установка

### Шаг 1: Установка интеграции

Вручную:

```bash
cd /config/custom_components/
# Скопируйте папку webhost1
```

Перезагрузите Home Assistant.

### Шаг 2: Настройка интеграции

Перейдите в **Настройки → Устройства и службы**

Нажмите **+ Добавить интеграцию**

Найдите **Webhost1**

Введите данные:

- ID аккаунта Webhost1
- Пароль Webhost1
- Интервал обновления (минуты)

Нажмите **Отправить**.

## 🔧 Настройка после установки

### Изменение пароля и интервала обновления

Перейдите в **Настройки → Устройства и службы**  
Найдите **Webhost1**  
Нажмите **Настроить**

Измените:

- пароль
- интервал обновления

### Что используется для входа

Для авторизации используется:

- ID аккаунта Webhost1
- пароль от аккаунта

Интеграция выполняет вход в личный кабинет через `login_check`, затем получает данные со страницы `/bp/orders`.

## 📱 Примеры использования

### Карточка заказа

```yaml
type: entities
title: Webhost1
entities:
  - entity: sensor.webhost1_order_1
    name: Сервер Webhost1
```

### Более подробная карточка

```yaml
type: entities
title: Webhost1 VPS
entities:
  - entity: sensor.webhost1_order_1
  - type: attribute
    entity: sensor.webhost1_order_1
    attribute: IP
    name: IP
  - type: attribute
    entity: sensor.webhost1_order_1
    attribute: due_date
    name: Срок оплаты
  - type: attribute
    entity: sensor.webhost1_order_1
    attribute: days_left
    name: Дней осталось
  - type: attribute
    entity: sensor.webhost1_order_1
    attribute: tariff
    name: Тариф
```

### Уведомление о скором окончании оплаты

```yaml
automation:
  - alias: "Webhost1: Скоро окончание оплаты"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.webhost1_order_1
        attribute: days_left
        below: 5
    actions:
      - action: notify.mobile_app
        data:
          title: "Webhost1"
          message: "До окончания оплаты осталось меньше 5 дней"
```

## 📄 Лицензия

MIT License

