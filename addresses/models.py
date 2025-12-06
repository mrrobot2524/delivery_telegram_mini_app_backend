from django.db import models
from telegram_users.models import TelegramUser


class UserAddress(models.Model):
    """Модель для хранения адресов доставки пользователя"""
    
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="addresses",
        help_text="Пользователь, которому принадлежит адрес"
    )
    title = models.CharField(
        max_length=100,
        help_text="Название адреса (например: 'Дом', 'Работа')"
    )
    address_text = models.CharField(
        max_length=255,
        help_text="Полный адрес доставки"
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Широта"
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Долгота"
    )
    entrance = models.CharField(
        max_length=20,
        blank=True,
        help_text="Подъезд"
    )
    floor = models.CharField(
        max_length=20,
        blank=True,
        help_text="Этаж"
    )
    apartment = models.CharField(
        max_length=20,
        blank=True,
        help_text="Квартира/офис"
    )
    intercom = models.CharField(
        max_length=50,
        blank=True,
        help_text="Код домофона"
    )
    comment = models.TextField(
        blank=True,
        help_text="Дополнительные комментарии (как пройти и т.д.)"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Адрес по умолчанию"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Адрес пользователя"
        verbose_name_plural = "Адреса пользователей"
        ordering = ["-is_default", "-created_at"]
        # Уникальность: у пользователя не может быть двух адресов с одинаковым названием
        unique_together = [["user", "title"]]

    def __str__(self):
        default_marker = " (по умолчанию)" if self.is_default else ""
        return f"{self.user.first_name} - {self.title}{default_marker}"

    def save(self, *args, **kwargs):
        # Если этот адрес устанавливается как default, снимаем флаг с других адресов пользователя
        if self.is_default:
            UserAddress.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
