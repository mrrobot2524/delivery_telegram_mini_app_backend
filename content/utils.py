from .models import UserNotification
import logging

logger = logging.getLogger(__name__)

def create_user_notification(telegram_id, title, message, notification_type='info', order=None):
    """
    Создать персональное уведомление для пользователя
    
    Args:
        telegram_id (int): Telegram ID пользователя
        title (str): Заголовок уведомления
        message (str): Текст уведомления
        notification_type (str): Тип уведомления
        order (Order, optional): Связанный заказ
        
    Returns:
        UserNotification: Созданное уведомление
    """
    try:
        notification = UserNotification.objects.create(
            telegram_id=telegram_id,
            title=title,
            message=message,
            notification_type=notification_type,
            order=order
        )
        logger.info(f"Notification created for user {telegram_id}: {title}")
        return notification
    except Exception as e:
        logger.error(f"Error creating notification for user {telegram_id}: {e}")
        return None
