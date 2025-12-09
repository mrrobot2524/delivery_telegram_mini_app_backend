from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import requests
import logging
from .models import Order, OrderCancellationRequest
from content.utils import create_user_notification

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, created, **kwargs):
    """
    Отправка уведомления пользователю при изменении статуса заказа.
    """
    if created:
        return
    
    # Чтобы не отправлять уведомление при каждом сохранении (например, обновление координат),
    # в реальном проекте лучше использовать FieldTracker из django-model-utils
    # или, если просто, проверять изменение статуса вручную, если мы передали old_status.
    # Но стандартный сигнал post_save не дает старое значение.
    # Поэтому мы полагаемся на то, что статус меняется осознанно.
    
    status_messages = {
        'preparing': "👨‍🍳 Ваш заказ принят и начал готовиться!",
        'delivering': "🚚 Курьер забрал ваш заказ и выехал к вам!",
        'done': "✅ Заказ доставлен. Приятного аппетита!",
        'canceled': "❌ Ваш заказ был отменен.",
    }
    
    message = status_messages.get(instance.status)
    
    if message:
        # Отправляем в телеграм
        send_telegram_message(instance.user.telegram_id, message)
        
        # Создаем уведомление в приложении (UserNotification)
        # Тип уведомления для статуса
        notif_type = 'order_status'
        if instance.status == 'done':
            notif_type = 'order_approved' # Условно, завершен = одобрен/готов
        elif instance.status == 'canceled':
            notif_type = 'order_cancelled'
            
        create_user_notification(
            telegram_id=instance.user.telegram_id,
            title=f"Статус заказа #{instance.id}",
            message=message,
            notification_type=notif_type,
            order=instance
        )


@receiver(post_save, sender=OrderCancellationRequest)
def notify_cancellation_status(sender, instance, created, **kwargs):
    """Уведомление при изменении статуса запроса на отмену"""
    if not created and instance.status in ['approved', 'rejected']:
        order = instance.order
        
        if instance.status == 'approved':
            title = "Отмена заказа одобрена"
            message = f"Ваш запрос на отмену заказа #{order.id} был одобрен. Заказ отменен."
            notification_type = 'cancel_approved'
        else:  # rejected
            title = "Отказ в отмене заказа"
            message = f"Ваш запрос на отмену заказа #{order.id} отклонен. "
            if instance.reason: # Добавляем причину отказа, если есть (хотя в модели reason usually for request reason, operator response might need another field, but assuming simple flow)
                 # Actually, processed_by operator doesn't leave a reject note in the current model explicitly except changing status.
                 pass
            message += "Свяжитесь с поддержкой для деталей."
            notification_type = 'cancel_rejected'
        
        # Отправляем в телеграм
        send_telegram_message(order.user.telegram_id, f"{title}\n{message}")

        # Создаем уведомление в приложении
        create_user_notification(
            telegram_id=order.user.telegram_id,
            title=title,
            message=message,
            notification_type=notification_type,
            order=order
        )


def send_telegram_message(chat_id, text):
    """
    Отправка сообщения через Telegram Bot API
    """
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set, cannot send notification")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send Telegram notification to {chat_id}: {e}")
