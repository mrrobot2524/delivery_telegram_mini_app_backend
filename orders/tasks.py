import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import requests
from .models import Order

logger = logging.getLogger(__name__)

@shared_task
def check_order_payment_status(order_id):
    """
    Периодическая задача для проверки статуса оплаты "зависших" заказов.
    (Можно вызывать раз в 5-10 минут)
    """
    try:
        order = Order.objects.get(id=order_id)
        if order.payment_status == 'paid':
            return "Already paid"
        
        # Здесь можно сделать запрос в Click API (CheckInvoice), если у них есть такой метод
        # Но обычно Click сам присылает вебхук.
        # Эта задача больше для очистки старых неоплаченных заказов.
        
        logger.info(f"Checking payment status for order {order_id}")
        return "Checked"
    except Order.DoesNotExist:
        return "Order not found"

@shared_task
def send_telegram_notification(chat_id, message):
    """
    Отправка сообщения в Telegram (фоновая задача RabbitMQ).
    """
    token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    try:
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        })
        response.raise_for_status()
        logger.info(f"Notification sent to {chat_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        # Celery может автоматически повторить задачу при сбое (retry)
        raise e

@shared_task
def process_successful_payment(order_id, amount):
    """
    Обработка успешного платежа:
    1. Обновление статуса заказа (если не обновлен)
    2. Уведомление менеджеров
    3. Генерация чека (в будущем)
    """
    try:
        order = Order.objects.get(id=order_id)
        
        # 1. Менеджеры (ID чата группы менеджеров - нужно добавить в настройки)
        # ADMIN_CHAT_ID = settings.ADMIN_CHAT_ID 
        # send_telegram_notification.delay(ADMIN_CHAT_ID, f"💰 Заказ #{order.id} ОПЛАЧЕН!\nСумма: {amount}")
        
        # 2. Уведомление пользователю
        send_telegram_notification.delay(
            order.user.telegram_id,
            f"✅ Оплата заказа #{order.id} прошла успешно!\nМы начали готовить ваши суши. 🍣"
        )
        
        logger.info(f"Payment processed for order {order_id}")
        return "Processed"
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found during payment processing")

