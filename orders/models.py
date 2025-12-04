from django.db import models

from telegram_users.models import TelegramUser
from menu.models import Product


class Order(models.Model):
    STATUS_CHOICES = (
        ("cart", "Корзина"),
        ("new", "Новый"),
        ("preparing", "Готовится"),
        ("delivering", "Доставляется"),
        ("done", "Доставлен"),
        ("canceled", "Отменён"),
    )

    DELIVERY_CHOICES = (
        ("pickup", "Самовывоз"),
        ("delivery", "Доставка"),
    )

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="cart",               # пока юзер собирает корзину
    )
    delivery_type = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        null=True,
        blank=True,
        help_text="Выбор: доставка или самовывоз",
    )
    address_text = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Адрес в свободной форме (улица, дом, подъезд)",
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Заказ #{self.id} от {self.user}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Цена за единицу на момент заказа",
    )

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def total_price(self):
        return self.price * self.quantity
