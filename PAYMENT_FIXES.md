# Исправление платежного потока - Полное решение

## Найденные и исправленные ошибки

### 1. Таблица `ClickTransaction` не существовала в БД ✅
**Ошибка:**
```
ProgrammingError: relation "orders_clicktransaction" does not exist
```

**Решение:**
```bash
python manage.py makemigrations orders
python manage.py migrate
```

### 2. Неправильный доступ к ID заказа в React ✅

**Проблема:**
- Метод `checkout` возвращает объект с `cart` и `active_orders`, а не прямой `id`
- Код пытался получить `response?.id`, что возвращал `undefined`

**Решение в `CheckoutModal.jsx`:**
```javascript
// ДО:
if (paymentMethod === "online" && response?.id) {
  order_id: response.id,  // ❌ undefined
}

// ПОСЛЕ:
const orderId = response?.active_orders?.[0]?.id;
if (paymentMethod === "online" && orderId) {
  order_id: orderId,  // ✅ правильный ID
}
```

### 3. Неправильный статус заказа в `InitiatePaymentView` ✅

**Проблема:**
- После `checkout` заказ получает статус `"new"`, а не `"cart"`
- `InitiatePaymentView` искал заказ со статусом `"cart"` → возвращала 404

**Решение в `InitiatePaymentView`:**
```python
# ДО:
order = Order.objects.get(id=order_id, user=tg_user, status="cart")  # ❌

# ПОСЛЕ:
order = Order.objects.get(id=order_id, user=tg_user, status="new")   # ✅
```

### 4. Constraint violation на `click_trans_id` ✅ (НОВОЕ)

**Ошибка:**
```
IntegrityError: duplicate key value violates unique constraint "orders_clicktransaction_click_trans_id_key"
Key (click_trans_id)=(0) already exists.
```

**Проблема:**
- Поле `click_trans_id` имело `unique=True`, но мы устанавливали его в 0 для новых транзакций
- Попытка создать вторую транзакцию вызывала конфликт уникальности

**Решение в `models.py`:**
```python
# ДО:
click_trans_id = models.BigIntegerField(
    unique=True,  # ❌ не позволяет несколько null
    help_text="ID транзакции Click"
)

# ПОСЛЕ:
click_trans_id = models.BigIntegerField(
    null=True,
    blank=True,
    help_text="ID транзакции Click (заполняется при callback)"
)
```

**Решение в `payment_service.py`:**
```python
# ДО:
transaction = ClickTransaction.objects.create(
    order=order,
    click_trans_id=0,  # ❌ вызывает конфликт
    merchant_trans_id=str(order.id),
    amount=order.final_price,
    status='pending',
)

# ПОСЛЕ:
transaction = ClickTransaction.objects.create(
    order=order,
    # click_trans_id будет установлена в callback, оставляем null
    merchant_trans_id=str(order.id),
    amount=order.final_price,
    status='pending',
)
```

**Миграция:**
```bash
python manage.py makemigrations orders
python manage.py migrate
# Миграция: orders.0009_alter_clicktransaction_click_trans_id
```

## Результаты тестирования

### Одиночный платеж:
```
✓ Checkout успешен - заказ создан
✓ Order ID получен из response.active_orders[0]
✓ Платеж инициирован без ошибок
✓ Payment URL возвращен корректно
✓ Mock callback URL готов для локального тестирования
```

### Множественные платежи подряд:
```
✓ Payment attempt #1: Transaction ID 5 ✓
✓ Payment attempt #2: Transaction ID 6 ✓
✓ Payment attempt #3: Transaction ID 7 ✓
✓ Все транзакции успешно созданы без конфликтов
✓ click_trans_id = None для новых платежей (заполняется при callback)
```

## Поток платежа (исправленный и работающий)

1. ✅ Пользователь выбирает "Онлайн оплата (Click)"
2. ✅ Click на "Оформить" → отправляется POST `/api/orders/checkout/`
3. ✅ Заказ создается со статусом `"new"`
4. ✅ Получаем ID заказа из `response.active_orders[0].id`
5. ✅ Вызываем POST `/api/orders/initiate-payment/` с order_id
6. ✅ Backend создает транзакцию в таблице `ClickTransaction` с `click_trans_id=NULL`
7. ✅ Возвращается `payment_url` (в dev: mock URL для локального тестирования)
8. ✅ React открывает платежную страницу в новой вкладке
9. ✅ Пользователь завершает платеж
10. ✅ Callback обновляет статус платежа на `"paid"` и заполняет `click_trans_id`

## Локальное тестирование

```bash
# Запустить сервер
python manage.py runserver

# Запустить тест платежа
python test_payment_flow.py

# Запустить тест множественных платежей
python test_multiple_payments.py
```

## Переменные окружения

По умолчанию для local dev:
```
CLICK_IS_MOCK=True
CLICK_MERCHANT_ID=12345
CLICK_MERCHANT_KEY=mock_key_local_dev
```

## Файлы которые были изменены

- ✅ `/orders/models.py` - изменен `click_trans_id` на nullable
- ✅ `/orders/views.py` - исправлен статус заказа, добавлено логирование
- ✅ `/orders/payment_service.py` - удаль установка `click_trans_id=0`
- ✅ `/src/components/CheckoutModal.jsx` - исправлен доступ к ID заказа

## Созданные миграции

- ✅ `orders/migrations/0008_alter_order_payment_method_clicktransaction.py` - создание модели
- ✅ `orders/migrations/0009_alter_clicktransaction_click_trans_id.py` - изменение на nullable
