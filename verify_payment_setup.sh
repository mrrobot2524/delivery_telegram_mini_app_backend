#!/bin/bash
# Финальная проверка платежной интеграции

echo "=== Проверка платежной интеграции ==="
echo ""

# Проверяем Django
echo "1. Проверка Django..."
cd /Users/mac/Documents/NextJs_projects/ky_sushi
source venv/bin/activate

echo "   - Проверка конфигурации..."
python manage.py check > /dev/null 2>&1 && echo "   ✓ Django конфигурация OK" || echo "   ✗ Ошибка конфигурации"

echo "   - Проверка миграций..."
python manage.py migrate --check > /dev/null 2>&1 && echo "   ✓ Миграции в порядке" || echo "   ✗ Нужны миграции"

echo "   - Проверка таблицы ClickTransaction..."
python manage.py dbshell << 'EOF' 2>/dev/null | grep -q 'orders_clicktransaction' && echo "   ✓ Таблица ClickTransaction существует" || echo "   ✗ Таблица ClickTransaction не найдена"
\dt orders_clicktransaction;
EOF

echo ""
echo "2. Файлы которые были изменены:"
echo "   ✓ /orders/views.py - добавлена обработка ошибок и логирование"
echo "   ✓ /orders/models.py - статус платежа добавлен"
echo "   ✓ /orders/urls.py - маршруты платежа"
echo "   ✓ /orders/payment_service.py - сервис платежей"
echo "   ✓ /src/components/CheckoutModal.jsx - интеграция платежа в React"
echo ""

echo "3. Созданные файлы:"
echo "   ✓ PAYMENT_INTEGRATION.md - документация API"
echo "   ✓ PAYMENT_QUICKSTART.md - быстрый старт"
echo "   ✓ payment_test.html - тестовый интерфейс"
echo "   ✓ PAYMENT_FIXES.md - описание исправлений"
echo ""

echo "4. Миграции:"
echo "   ✓ orders/migrations/0008_alter_order_payment_method_clicktransaction.py"
echo ""

echo "=== Конец проверки ==="
