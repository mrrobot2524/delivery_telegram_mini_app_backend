#!/usr/bin/env python
"""
Тестовый скрипт для проверки Celery
"""
import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from orders.tasks import send_telegram_notification

# Отправляем тестовое уведомление
print("Отправка тестовой задачи в Celery...")
result = send_telegram_notification.delay(
    chat_id=999999999,  # Тестовый ID
    message="🎉 Celery работает! Это тестовое сообщение."
)

print(f"✅ Задача отправлена!")
print(f"Task ID: {result.id}")
print(f"Status: {result.status}")

# Ждем результат
print("\nОжидание выполнения задачи...")
import time
time.sleep(3)

print(f"Final Status: {result.status}")
if result.ready():
    print(f"Result: {result.result}")
else:
    print("Задача еще выполняется...")

print("\n✅ Тест завершен!")
print("Проверьте результаты в админке: http://localhost:8000/admin/django_celery_results/taskresult/")
