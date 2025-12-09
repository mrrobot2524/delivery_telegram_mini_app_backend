# ✅ Проверка интеграции промокода и оплаты

**Результат:** Интеграция работает корректно.

## Детали проверки:

1.  **Модель заказа (`orders/models.py` - `Order`):**
    -   Содержит поля `promo_code` и `discount_amount`.
    -   Свойство `final_price` правильно вычисляет итоговую сумму: `total_price - discount_amount`.

2.  **Процессор оплаты (`orders/payment_service.py`):**
    -   При создании платежной ссылки (для Click) используется `order.final_price`.
    -   `ClickTransaction` также создается с суммой `order.final_price`.

Это означает, что если пользователь применит промокод в корзине, сумма к оплате в Click будет **со скидкой**.

## Рекомендации:
- Убедитесь, что в `.env` заполнены параметры Click (`CLICK_SERVICE_ID`, `CLICK_MERCHANT_ID`, `CLICK_SECRET_KEY`).
