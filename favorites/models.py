from django.db import models
from telegram_users.models import TelegramUser
from menu.models import Product


class Favorite(models.Model):
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="favorites"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.product.name}"
