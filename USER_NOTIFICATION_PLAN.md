"""
Создание модели UserNotification для персональных уведомлений пользователей
"""

from django.db import models
from django.conf import settings


class UserNotification(models.Model):
    """Персональные уведомления для пользователей"""
    
    TYPE_CHOICES = [
        ('order_approved', 'Заказ одобрен'),
        ('order_rejected', 'Заказ отклонен'),
        ('order_status', 'Статус заказа'),
        ('promo', 'Акция'),
        ('info', 'Информация'),
    ]
    
    telegram_id = models.BigIntegerField(verbose_name="Telegram ID пользователя", db_index=True)
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    message = models.TextField(verbose_name="Сообщение")
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='info',
        verbose_name="Тип"
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="Заказ"
    )
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Уведомление пользователя"
        verbose_name_plural = "Уведомления пользователей"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['telegram_id', '-created_at']),
            models.Index(fields=['telegram_id', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.telegram_id}"
