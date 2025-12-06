from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import requests
import logging
from .models import Order

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
    
    # Для MVP будем отправлять уведомление всегда, когда статус не 'cart' и не 'new'
    # (потому что 'new' ставится при создании заказа, пользователь и так знает).
    
    # UPD: Лучший способ без tracker'а - проверять статус
    
    status_messages = {
        'preparing': "👨‍🍳 Ваш заказ принят и начал готовиться!",
        'delivering': "🚚 Курьер забрал ваш заказ и выехал к вам!",
        'done': "✅ Заказ доставлен. Приятного аппетита!",
        'canceled': "❌ Ваш заказ был отменен.",
    }
    
    message = status_messages.get(instance.status)
    
    if not message:
        return
        
    # Проверяем, не отправляли ли мы уже это уведомление (можно добавить поле last_notified_status в модель)
    # Но пока просто шлем.
    
    send_telegram_message(instance.user.telegram_id, message)


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
