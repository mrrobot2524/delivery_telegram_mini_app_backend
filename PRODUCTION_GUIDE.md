# 🚀 Памятка: Переход в боевой режим (Production)

## 1. Настройка оплаты (Payme / Click)

### Payme (Telegram Payments)
В файле `.env` найдите строку:
```bash
PAYME_PROVIDER_TOKEN=371317599:TEST:1765199362697
```
Замените значение на ваш **Live-токен**, который вы получили от Paycom/Telegram.
Пример:
```bash
PAYME_PROVIDER_TOKEN=123456789:LIVE:AbCdEfGhIjKlMnOpQrSt
```

### Click
Убедитесь, что в `.env` заполнены боевые данные:
```bash
CLICK_SERVICE_ID=...
CLICK_MERCHANT_ID=...
CLICK_SECRET_KEY=...
# Важно: отключите мок-режим
CLICK_IS_MOCK=False
```

---

## 2. RabbitMQ (Очереди задач)

Строка в `.env`:
```bash
# CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
```
Она нужна для подключения к RabbitMQ.
- Если вы используете стандартный локальный RabbitMQ (установленный через brew или docker без пароля), трогать эту строку не нужно (код использует эти значения по умолчанию).
- Если вы настроите RabbitMQ на отдельном сервере или зададите пароль, раскомментируйте строку и впишите свои данные: `amqp://user:password@ip:port//`.

---

## 3. Перезапуск

После любых изменений в `.env` файле **обязательно** перезапускайте:
1.  **Backend:** `python manage.py runserver` (или перезапуск сервиса gunicorn/systemd).
2.  **Bot:** `python manage.py runbot`.
3.  **Celery:** (если запущен) перезапуск воркера.
