from django.db import models

class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)  # Изменено с second_name на last_name
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    photo_file_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="file_id аватарки из Telegram"
    )
    
    photo = models.ImageField(
        upload_to="telegram_avatars/",
        null=True,
        blank=True,
    )
    
    is_admin = models.BooleanField(default=False, help_text="Является ли пользователь администратором")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Как будет отображаться в админке
        return f"{self.first_name or ''} (@{self.username})"
