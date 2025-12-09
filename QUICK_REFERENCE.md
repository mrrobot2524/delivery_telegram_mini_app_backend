# 🚀 Шпаргалка: Быстрые команды и ссылки

## 📍 Быстрый доступ к админке

### Основные разделы
```
Адреса пользователей:
http://localhost:8000/admin/addresses/useraddress/

Заказы:
http://localhost:8000/admin/orders/order/

Запросы на отмену товаров:
http://localhost:8000/admin/orders/orderitemcancellationrequest/

Запросы на отмену заказов:
http://localhost:8000/admin/orders/ordercancellationrequest/

Акции (Promotions):
http://localhost:8000/admin/orders/promotion/

Промокоды:
http://localhost:8000/admin/orders/promocode/

Celery Task Results:
http://localhost:8000/admin/django_celery_results/taskresult/

Периодические задачи:
http://localhost:8000/admin/django_celery_beat/periodictask/
```

---

## ⚡ Быстрые команды

### Запуск проекта
```bash
# Django сервер
python manage.py runserver

# Celery Worker
celery -A core worker --loglevel=info

# Celery Beat
celery -A core beat --loglevel=info

# Фронтенд (в папке ky_sushi_front)
npm run dev
```

### Celery команды
```bash
# Проверить зарегистрированные задачи
celery -A core inspect registered

# Проверить активные задачи
celery -A core inspect active

# Очистить очередь
celery -A core purge

# Запустить Flower (мониторинг)
celery -A core flower
# Откройте: http://localhost:5555
```

### Django команды
```bash
# Создать миграции
python manage.py makemigrations

# Применить миграции
python manage.py migrate

# Создать суперпользователя
python manage.py createsuperuser

# Собрать статику
python manage.py collectstatic

# Запустить shell
python manage.py shell
```

---

## 🧪 Быстрое тестирование

### Тест 1: Проверка акций
```bash
# 1. Создайте акцию в админке
open http://localhost:8000/admin/orders/promotion/add/

# 2. Проверьте API
curl http://localhost:8000/api/menu/products/?category_id=1 | jq

# Должны увидеть: "discounted_price", "has_promotion"
```

### Тест 2: Отправка уведомления
```bash
python manage.py shell
```
```python
from orders.tasks import send_telegram_notification

# Замените на свой telegram_id
send_telegram_notification.delay(123456789, "Test message")
```

### Тест 3: Проверка корзины
```bash
# Получить корзину пользователя
curl -H "X-Telegram-Init-Data: query_id=..." \
     http://localhost:8000/api/orders/cart/
```

---

## 📁 Важные файлы

### Конфигурация
```
core/settings.py          # Настройки Django
core/celery.py           # Настройки Celery
.env                     # Переменные окружения
```

### Модели
```
orders/models.py         # Order, OrderItem, Promotion, PromoCode
menu/models.py          # Product, Category
addresses/models.py     # UserAddress
telegram_users/models.py # TelegramUser
```

### API
```
orders/views.py         # API для заказов и корзины
menu/views.py          # API для товаров
addresses/views.py     # API для адресов
```

### Задачи
```
orders/tasks.py        # Celery задачи
```

### Админка
```
orders/admin.py        # Админка заказов
addresses/admin.py     # Админка адресов
telegram_users/admin.py # Админка пользователей
```

---

## 🔧 Быстрые исправления

### Исправить акции (3 шага)
```bash
# 1. Открыть файл
code menu/models.py

# 2. Добавить метод get_discounted_price() (см. FIX_PROMOTIONS_GUIDE.md)

# 3. Изменить orders/views.py
# defaults={"price": product.get_discounted_price()}
```

### Запустить Celery (1 команда)
```bash
celery -A core worker --loglevel=info
```

### Создать периодическую задачу (через админку)
```
1. http://localhost:8000/admin/django_celery_beat/periodictask/add/
2. Name: "Check Payment Status"
3. Task: orders.tasks.check_order_payment_status
4. Interval: Создать новый (10 минут)
5. Enabled: ✅
6. Сохранить
```

---

## 🐛 Решение проблем

### Ошибка: "No module named 'celery'"
```bash
pip install celery
```

### Ошибка: "Broker connection error"
```bash
mkdir -p broker/in broker/out broker/processed
```

### Ошибка: "Task not registered"
```bash
# Проверьте, что задача импортируется
celery -A core inspect registered
```

### Ошибка: "CORS error"
```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

---

## 📊 Полезные запросы

### SQL: Найти все активные акции
```sql
SELECT * FROM orders_promotion 
WHERE is_active = true 
  AND valid_from <= NOW() 
  AND valid_until >= NOW();
```

### Django ORM: Товары с акциями
```python
from menu.models import Product
from django.utils import timezone

products_with_promotions = Product.objects.filter(
    promotions__is_active=True,
    promotions__valid_from__lte=timezone.now(),
    promotions__valid_until__gte=timezone.now()
).distinct()
```

### Django ORM: Неоплаченные заказы
```python
from orders.models import Order

pending_orders = Order.objects.filter(
    payment_status='pending',
    status__in=['new', 'preparing']
)
```

---

## 🔗 Полезные ссылки

### Документация
- Django: https://docs.djangoproject.com/
- Celery: https://docs.celeryq.dev/
- DRF: https://www.django-rest-framework.org/
- Leaflet: https://leafletjs.com/

### Внутренние документы
- `ADMIN_CELERY_ANALYSIS.md` - подробный анализ
- `FIX_PROMOTIONS_GUIDE.md` - исправление акций
- `CELERY_QUICKSTART.md` - запуск Celery
- `PROJECT_STATUS.md` - состояние проекта
- `ANSWERS_TO_QUESTIONS.md` - ответы на вопросы

---

## 📞 API Endpoints

### Меню
```
GET  /api/menu/categories/           # Список категорий
GET  /api/menu/products/             # Список товаров
GET  /api/menu/products/{id}/        # Детали товара
```

### Заказы
```
GET    /api/orders/cart/             # Получить корзину
POST   /api/orders/cart/             # Добавить в корзину
PATCH  /api/orders/cart/             # Обновить корзину
DELETE /api/orders/cart/             # Очистить корзину

POST   /api/orders/checkout/         # Оформить заказ
GET    /api/orders/my/               # Мои заказы
```

### Адреса
```
GET    /api/addresses/               # Список адресов
POST   /api/addresses/               # Создать адрес
PATCH  /api/addresses/{id}/          # Обновить адрес
DELETE /api/addresses/{id}/          # Удалить адрес
```

---

## ⌨️ Горячие клавиши (VS Code)

```
Cmd + P         # Быстрый поиск файла
Cmd + Shift + F # Поиск по всем файлам
Cmd + `         # Открыть терминал
Cmd + B         # Скрыть/показать сайдбар
Cmd + /         # Закомментировать строку
```

---

**Дата:** 2025-12-08  
**Проект:** KY Sushi  
**Автор:** Antigravity AI
