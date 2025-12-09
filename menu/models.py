from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=255)          # Холодные роллы
    slug = models.SlugField(unique=True)             # holodnye-rolly
    is_active = models.BooleanField(default=True)
    is_for_app = models.BooleanField(default=True, verbose_name="Показывать в Telegram")
    is_for_qr = models.BooleanField(default=True, verbose_name="Показывать в QR меню")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=255)          # Запечённые роллы с угрём
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/") # фото товара [web:146][web:152]
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    is_for_app = models.BooleanField(default=True, verbose_name="Показывать в Telegram")
    is_for_qr = models.BooleanField(default=True, verbose_name="Показывать в QR меню")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["category", "name"]

    def __str__(self):
        return self.name
    
    def get_discounted_price(self):
        """
        Получить цену с учетом активных акций.
        Если акций нет - возвращает обычную цену.
        """
        from django.utils import timezone
        from orders.models import Promotion
        
        # Находим активные акции для этого товара
        active_promotions = self.promotions.filter(
            is_active=True,
            valid_from__lte=timezone.now(),
            valid_until__gte=timezone.now()
        )
        
        # Если акций нет - возвращаем обычную цену
        if not active_promotions.exists():
            return self.price
        
        # Берем первую акцию (можно изменить логику на "самую выгодную")
        promo = active_promotions.first()
        
        # Рассчитываем скидку
        if promo.discount_type == 'percentage':
            discount = (self.price * promo.discount_value) / 100
            return self.price - discount
        else:  # fixed
            return max(self.price - promo.discount_value, 0)
    
    def get_active_promotion(self):
        """
        Получить активную акцию для товара (если есть).
        """
        from django.utils import timezone
        from orders.models import Promotion
        
        return self.promotions.filter(
            is_active=True,
            valid_from__lte=timezone.now(),
            valid_until__gte=timezone.now()
        ).first()
