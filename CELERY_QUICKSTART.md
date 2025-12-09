# 🚀 Быстрый старт: Запуск Celery в проекте KY Sushi

## 📋 Что такое Celery и зачем он нужен?

**Celery** - это система для выполнения фоновых задач в Python/Django.

**Зачем нужен в вашем проекте:**
1. ✅ Отправка уведомлений в Telegram (не блокирует HTTP-запрос)
2. ✅ Проверка статуса оплаты через Click API
3. ✅ Автоматическая очистка старых корзин
4. ✅ Генерация отчетов
5. ✅ Любые долгие операции

---

## ⚡ Быстрый запуск (3 команды)

### Вариант 1: Все в одном терминале (для тестирования)

```bash
# Перейдите в папку проекта
cd /Users/mac/Documents/NextJs_projects/ky_sushi

# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите Celery Worker
celery -A core worker --loglevel=info
```

**Что увидите:**
```
 -------------- celery@MacBook-Pro v5.x.x
---- **** ----- 
--- * ***  * -- Darwin-xx.x.x
-- * - **** --- 
- ** ---------- [config]
- ** ---------- .> app:         core:0x...
- ** ---------- .> transport:   filesystem://...
- ** ---------- .> results:     django-db
- *** --- * --- .> concurrency: 8 (prefork)
-- ******* ---- .> task events: OFF
--- ***** ----- 
 -------------- [queues]
                .> celery           exchange=celery(direct) key=celery

[tasks]
  . orders.tasks.check_order_payment_status
  . orders.tasks.process_successful_payment
  . orders.tasks.send_telegram_notification

[2024-12-08 13:00:00,000: INFO/MainProcess] Connected to filesystem://...
[2024-12-08 13:00:00,000: INFO/MainProcess] celery@MacBook-Pro ready.
```

✅ **Готово!** Celery запущен и готов выполнять задачи.

---

### Вариант 2: Профессиональный запуск (3 терминала)

#### Терминал 1: Django сервер
```bash
cd /Users/mac/Documents/NextJs_projects/ky_sushi
source venv/bin/activate
python manage.py runserver
```

#### Терминал 2: Celery Worker
```bash
cd /Users/mac/Documents/NextJs_projects/ky_sushi
source venv/bin/activate
celery -A core worker --loglevel=info
```

#### Терминал 3: Celery Beat (для периодических задач)
```bash
cd /Users/mac/Documents/NextJs_projects/ky_sushi
source venv/bin/activate
celery -A core beat --loglevel=info
```

---

## 🧪 Тестирование: Отправка тестового уведомления

### Способ 1: Через Django Shell

```bash
python manage.py shell
```

```python
from orders.tasks import send_telegram_notification

# Отправить уведомление себе (замените на свой chat_id)
result = send_telegram_notification.delay(
    chat_id=123456789,  # ← Ваш Telegram ID
    message="🎉 Celery работает!"
)

print(f"Task ID: {result.id}")
print(f"Status: {result.status}")
```

### Способ 2: Через админку

1. Откройте `/admin/django_celery_results/taskresult/`
2. Вы увидите список выполненных задач
3. Кликните на задачу, чтобы увидеть результат

---

## 📅 Настройка периодических задач

### Шаг 1: Создайте периодическую задачу через админку

1. Откройте `/admin/django_celery_beat/periodictask/add/`

2. Заполните форму:
   - **Name:** `Check Payment Status Every 10 Minutes`
   - **Task (registered):** `orders.tasks.check_order_payment_status`
   - **Enabled:** ✅ Да
   
3. Создайте интервал:
   - Кликните на "+" рядом с **Interval**
   - **Every:** `10`
   - **Period:** `Minutes`
   - Сохраните

4. Выберите созданный интервал в поле **Interval**

5. **Arguments:** `[]` (пустой JSON массив)

6. Сохраните

### Шаг 2: Проверьте, что задача запланирована

```bash
# В терминале с Celery Beat вы увидите:
[2024-12-08 13:00:00,000: INFO/MainProcess] Scheduler: Sending due task Check Payment Status Every 10 Minutes (orders.tasks.check_order_payment_status)
```

---

## 🛠️ Полезные команды

### Проверить статус задачи

```python
from celery.result import AsyncResult

result = AsyncResult('task-id-here')
print(result.status)  # PENDING, SUCCESS, FAILURE
print(result.result)  # Результат выполнения
```

### Очистить очередь задач

```bash
celery -A core purge
```

### Посмотреть активные задачи

```bash
celery -A core inspect active
```

### Посмотреть зарегистрированные задачи

```bash
celery -A core inspect registered
```

---

## 🐛 Решение проблем

### Проблема: "No module named 'celery'"

**Решение:**
```bash
pip install celery
```

### Проблема: "Broker connection error"

**Решение:**
Проект использует файловый брокер. Убедитесь, что папки существуют:
```bash
mkdir -p broker/in broker/out broker/processed
```

### Проблема: Задачи не выполняются

**Проверьте:**
1. ✅ Celery Worker запущен
2. ✅ Задача зарегистрирована (см. вывод при запуске worker)
3. ✅ Нет ошибок в логах

**Посмотрите логи:**
```bash
# В терминале с Celery Worker
# Ищите строки с [ERROR] или [WARNING]
```

### Проблема: Периодические задачи не запускаются

**Проверьте:**
1. ✅ Celery Beat запущен
2. ✅ Задача включена (Enabled = True)
3. ✅ Интервал настроен правильно

---

## 📊 Мониторинг (опционально)

### Установка Flower (веб-интерфейс для Celery)

```bash
pip install flower
```

### Запуск Flower

```bash
celery -A core flower
```

Откройте в браузере: `http://localhost:5555`

**Что увидите:**
- 📊 Графики выполнения задач
- 📝 Список активных задач
- ✅ Успешные задачи
- ❌ Ошибки
- 👷 Статус воркеров

---

## 🎯 Примеры использования в коде

### Пример 1: Отправка уведомления после создания заказа

```python
# orders/views.py
from .tasks import send_telegram_notification

def create_order(request):
    # ... создание заказа ...
    
    # Отправляем уведомление в фоне
    send_telegram_notification.delay(
        chat_id=request.user.telegram_id,
        message=f"✅ Заказ #{order.id} создан!"
    )
    
    return Response({"status": "ok"})
```

### Пример 2: Обработка платежа в фоне

```python
# orders/views.py
from .tasks import process_successful_payment

def payment_callback(request):
    # ... проверка подписи Click ...
    
    # Обрабатываем платеж в фоне
    process_successful_payment.delay(
        order_id=order.id,
        amount=amount
    )
    
    return Response({"error": 0})
```

### Пример 3: Отложенная задача (через 5 минут)

```python
from datetime import timedelta
from django.utils import timezone

# Отправить напоминание через 5 минут
send_telegram_notification.apply_async(
    args=[chat_id, "⏰ Не забудьте оплатить заказ!"],
    eta=timezone.now() + timedelta(minutes=5)
)
```

---

## ✅ Чек-лист: Celery настроен правильно

- ✅ `celery` установлен (`pip install celery`)
- ✅ `django_celery_results` в `INSTALLED_APPS`
- ✅ `django_celery_beat` в `INSTALLED_APPS`
- ✅ `core/celery.py` существует
- ✅ `core/__init__.py` импортирует `celery_app`
- ✅ Папки `broker/in`, `broker/out`, `broker/processed` существуют
- ✅ Celery Worker запускается без ошибок
- ✅ Задачи видны в выводе Worker
- ✅ Тестовая задача выполняется успешно

---

## 🚀 Готово к продакшену?

Для продакшена рекомендуется:

1. **Использовать Redis вместо файлового брокера:**
   ```python
   # settings.py
   CELERY_BROKER_URL = 'redis://localhost:6379/0'
   ```

2. **Запускать Celery через systemd/supervisor:**
   ```bash
   # /etc/systemd/system/celery.service
   [Unit]
   Description=Celery Service
   After=network.target

   [Service]
   Type=forking
   User=www-data
   Group=www-data
   WorkingDirectory=/path/to/project
   ExecStart=/path/to/venv/bin/celery -A core worker --loglevel=info

   [Install]
   WantedBy=multi-user.target
   ```

3. **Настроить логирование:**
   ```python
   # settings.py
   CELERY_TASK_TRACK_STARTED = True
   CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 минут
   ```

---

**Автор:** Antigravity AI  
**Дата:** 2025-12-08  
**Проект:** KY Sushi
