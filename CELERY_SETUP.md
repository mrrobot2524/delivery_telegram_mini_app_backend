# 🐰 Инструкция по запуску RabbitMQ + Celery

Эта инструкция поможет запустить очереди задач для надежной обработки платежей, уведомлений и других фоновых процессов.

## 1. Установка RabbitMQ

Вам нужно установить сервер очередей RabbitMQ. Если у вас Mac:

```bash
brew install rabbitmq
```

После установки запустите сервис:

```bash
brew services start rabbitmq
```
_Или просто запустите `rabbitmq-server` в отдельном терминале._

По умолчанию RabbitMQ работает на порту `5672`.

## 2. Настройка проекта

Я уже настроил Django для работы с Celery в файлах:
- `ky_sushi/core/celery.py` — конфигурация приложения.
- `ky_sushi/core/settings.py` — настройки брокера (RabbitMQ) и бэкенда для результатов (Django DB).

## 3. Запуск Celery Worker

Чтобы задачи начали выполняться, нужно запустить "рабочего" (worker). Откройте **новый терминал**, перейдите в папку с проектом и выполните:

```bash
# Активируйте виртуальное окружение, если нужно
source venv/bin/activate

# Запуск воркера (в режиме разработки)
celery -A core worker --loglevel=info
```

Если вы видите лог запуска с "bunny" (кроликом) — значит всё работает! 🎉

## 4. Как использовать в коде

Пример создания задачи. Создайте файл `tasks.py` внутри любого приложения (например `orders/tasks.py`):

```python
from celery import shared_task

@shared_task
def send_payment_notification(order_id):
    # Долгая операция, например отправка SMS или запроса в Telegram
    print(f"Отправляем уведомление для заказа {order_id}...")
    return "Done"
```

Вызов задачи из views.py:
```python
from .tasks import send_payment_notification

def my_view(request):
    # ...
    # Задача улетит в RabbitMQ и выполнится фоном
    send_payment_notification.delay(order.id)
    return HttpResponse("Заказ обрабатывается")
```

## 5. Мониторинг (Опционально)

Для удобного просмотра задач можно установить Flower:
```bash
pip install flower
celery -A core flower
```
И открыть `http://localhost:5555`.
