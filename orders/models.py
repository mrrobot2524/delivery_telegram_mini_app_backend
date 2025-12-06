from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from telegram_users.models import TelegramUser
from menu.models import Product


class PromoCode(models.Model):
    """Модель промокода для скидок"""
    DISCOUNT_TYPE_CHOICES = (
        ("percentage", "Процент"),
        ("fixed", "Фиксированная сумма"),
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Уникальный код промокода (например: SUMMER2024)"
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default="percentage",
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Значение скидки (процент или сумма)",
    )
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Минимальная сумма заказа для применения промокода",
    )
    max_uses = models.PositiveIntegerField(
        default=0,
        help_text="Максимальное количество использований (0 = без ограничений)",
    )
    current_uses = models.PositiveIntegerField(
        default=0,
        help_text="Текущее количество использований",
    )
    valid_from = models.DateTimeField(
        help_text="Дата начала действия промокода"
    )
    valid_until = models.DateTimeField(
        help_text="Дата окончания действия промокода"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Активен ли промокод",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()})"

    def is_valid(self):
        """Проверка валидности промокода"""
        now = timezone.now()
        if not self.is_active:
            return False, "Промокод неактивен"
        if now < self.valid_from:
            return False, "Промокод еще не действует"
        if now > self.valid_until:
            return False, "Промокод истек"
        if self.max_uses > 0 and self.current_uses >= self.max_uses:
            return False, "Превышен лимит использований промокода"
        return True, "OK"

    def calculate_discount(self, order_total):
        """Расчет суммы скидки"""
        if order_total < self.min_order_amount:
            return 0
        
        if self.discount_type == "percentage":
            return (order_total * self.discount_value) / 100
        else:  # fixed
            return min(self.discount_value, order_total)


class Promotion(models.Model):
    """Модель акции на товары"""
    DISCOUNT_TYPE_CHOICES = (
        ("percentage", "Процент"),
        ("fixed", "Фиксированная сумма"),
    )

    name = models.CharField(
        max_length=255,
        help_text="Название акции",
    )
    description = models.TextField(
        blank=True,
        help_text="Описание акции",
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default="percentage",
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Значение скидки",
    )
    products = models.ManyToManyField(
        Product,
        related_name="promotions",
        help_text="Товары, участвующие в акции",
    )
    valid_from = models.DateTimeField(
        help_text="Дата начала акции"
    )
    valid_until = models.DateTimeField(
        help_text="Дата окончания акции"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Активна ли акция",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def is_valid(self):
        """Проверка валидности акции"""
        now = timezone.now()
        return (
            self.is_active
            and self.valid_from <= now <= self.valid_until
        )


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
        default="cart",
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

    # Промокод и скидки
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="Примененный промокод",
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Сумма скидки",
    )
    
    # Дополнительные поля
    estimated_time = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ориентировочное время готовности (например: '30-40 минут')",
    )
    
    # Поля оплаты
    PAYMENT_METHOD_CHOICES = (
        ("cash", "Наличные при получении"),
        ("card", "Картой курьеру"),
        ("online", "Онлайн оплата"),
    )
    
    PAYMENT_STATUS_CHOICES = (
        ("pending", "Ожидает оплаты"),
        ("paid", "Оплачено"),
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="cash",
        help_text="Способ оплаты",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending",
        help_text="Статус оплаты",
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Дата и время оплаты",
    )

    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заказ #{self.id} от {self.user}"

    @property
    def total_price(self):
        """Сумма заказа без учета скидки"""
        return sum(item.total_price for item in self.items.filter(is_canceled=False))

    @property
    def final_price(self):
        """Итоговая сумма с учетом скидки"""
        total = self.total_price
        return max(total - self.discount_amount, 0)

    def apply_promo_code(self, promo_code):
        """Применение промокода к заказу"""
        is_valid, message = promo_code.is_valid()
        if not is_valid:
            raise ValidationError(message)
        
        total = self.total_price
        if total < promo_code.min_order_amount:
            raise ValidationError(
                f"Минимальная сумма заказа для этого промокода: {promo_code.min_order_amount}"
            )
        
        self.promo_code = promo_code
        self.discount_amount = promo_code.calculate_discount(total)
        self.save()
        
        # Увеличиваем счетчик использований
        promo_code.current_uses += 1
        promo_code.save()


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
    
    # Поля для отмены товара
    is_canceled = models.BooleanField(
        default=False,
        help_text="Отменен ли товар",
    )
    canceled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Дата и время отмены",
    )

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self):
        status = " (отменен)" if self.is_canceled else ""
        return f"{self.product.name} x{self.quantity}{status}"

    @property
    def total_price(self):
        """Общая стоимость позиции (цена × количество)"""
        if self.price is None:
            return 0
        if self.is_canceled:
            return 0
        return self.price * self.quantity


class OrderItemCancellationRequest(models.Model):
    """Запрос на отмену товара в заказе"""
    STATUS_CHOICES = (
        ("pending", "Ожидает обработки"),
        ("approved", "Одобрен"),
        ("rejected", "Отклонен"),
    )

    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="cancellation_requests",
    )
    requested_by = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="cancellation_requests",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    reason = models.TextField(
        blank=True,
        help_text="Причина отмены",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    
    processed_by = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_cancellations",
        help_text="Оператор, обработавший запрос",
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Дата и время обработки",
    )

    class Meta:
        verbose_name = "Запрос: Отмена ТОВАРА"
        verbose_name_plural = "Запросы: Отмена ТОВАРОВ"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Запрос на отмену {self.order_item} ({self.get_status_display()})"

    def approve(self, operator):
        """Одобрение запроса на отмену"""
        self.status = "approved"
        self.processed_by = operator
        self.processed_at = timezone.now()
        self.save()
        
        # Отменяем товар
        self.order_item.is_canceled = True
        self.order_item.canceled_at = timezone.now()
        self.order_item.save()

    def reject(self, operator):
        """Отклонение запроса на отмену"""
        self.status = "rejected"
        self.processed_by = operator
        self.processed_at = timezone.now()
        self.save()


class OrderCancellationRequest(models.Model):
    """Запрос на полную отмену заказа"""
    STATUS_CHOICES = (
        ("pending", "Ожидает обработки"),
        ("approved", "Одобрен"),
        ("rejected", "Отклонен"),
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="cancellation_requests",
    )
    requested_by = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="order_cancellation_requests",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    reason = models.TextField(
        blank=True,
        help_text="Причина отмены",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    
    processed_by = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_order_cancellations",
        help_text="Оператор, обработавший запрос",
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Дата и время обработки",
    )

    class Meta:
        verbose_name = "Запрос: Отмена ЗАКАЗА"
        verbose_name_plural = "Запросы: Отмена ЗАКАЗОВ"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Запрос на отмену {self.order} ({self.get_status_display()})"

    def approve(self, operator):
        """Одобрение запроса на отмену"""
        self.status = "approved"
        self.processed_by = operator
        self.processed_at = timezone.now()
        self.save()
        
        # Отменяем заказ
        self.order.status = "canceled"
        self.order.save()

    def reject(self, operator):
        """Отклонение запроса на отмену"""
        self.status = "rejected"
        self.processed_by = operator
        self.processed_at = timezone.now()
        self.save()


class ClickTransaction(models.Model):
    """Модель для отслеживания транзакций Click"""
    STATUS_CHOICES = (
        ('pending', 'Ожидает'),
        ('preparing', 'Подготовка'),
        ('confirmed', 'Подтверждено'),
        ('canceled', 'Отменено'),
        ('error', 'Ошибка'),
    )
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='click_transactions',
        help_text="Связанный заказ"
    )
    click_trans_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ID транзакции Click (заполняется при callback)"
    )
    merchant_trans_id = models.CharField(
        max_length=255,
        help_text="ID заказа (order.id)"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Сумма платежа"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Prepare данные
    merchant_prepare_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ID подготовки транзакции"
    )
    prepare_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Время подготовки"
    )
    
    # Complete данные
    complete_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Время завершения"
    )
    error_code = models.IntegerField(
        null=True,
        blank=True,
        help_text="Код ошибки от Click"
    )
    error_note = models.TextField(
        blank=True,
        help_text="Описание ошибки"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Click Транзакция"
        verbose_name_plural = "Click Транзакции"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"Click #{self.click_trans_id} - Order #{self.order.id} ({self.get_status_display()})"
