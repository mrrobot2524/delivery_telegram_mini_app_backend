from django.db import models


class Notification(models.Model):
    """Модель для уведомлений пользователям"""
    TYPE_CHOICES = [
        ('info', 'Информация'),
        ('promo', 'Акция'),
        ('order', 'Заказ'),
        ('news', 'Новость'),
    ]
    
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    message = models.TextField(verbose_name="Сообщение")
    notification_type = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES, 
        default='info', 
        verbose_name="Тип"
    )
    image = models.ImageField(
        upload_to='notifications/', 
        null=True, 
        blank=True, 
        verbose_name="Изображение"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class ContentPage(models.Model):
    """Модель для хранения контентных страниц (о нас, доставка, оплата и т.д.)"""
    TITLE_CHOICES = [
        ('about', 'О нас'),
        ('delivery', 'Доставка'),
        ('payment', 'Оплата'),
        ('offer', 'Публичная оферта'),
        ('privacy', 'Политика конфиденциальности'),
        ('mobile_app', 'Мобильное приложение'),
    ]
    
    title = models.CharField(max_length=50, choices=TITLE_CHOICES, unique=True, verbose_name="Название")
    content = models.TextField(verbose_name="Содержание")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Контентная страница"
        verbose_name_plural = "Контентные страницы"
        ordering = ['title']
    
    def __str__(self):
        return dict(self.TITLE_CHOICES)[self.title]


class Branch(models.Model):
    """Модель для филиалов"""
    name = models.CharField(max_length=255, verbose_name="Название")
    address = models.CharField(max_length=500, verbose_name="Адрес")
    phone = models.CharField(max_length=50, verbose_name="Телефон")
    working_hours = models.CharField(max_length=255, verbose_name="Часы работы")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Широта")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Долгота")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Филиал"
        verbose_name_plural = "Филиалы"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Promotion(models.Model):
    """Модель для акций"""
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    image = models.ImageField(upload_to='promotions/', null=True, blank=True, verbose_name="Изображение")
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"
        ordering = ['-start_date']
    
    def __str__(self):
        return self.title


class Vacancy(models.Model):
    """Модель для вакансий"""
    title = models.CharField(max_length=255, verbose_name="Название должности")
    description = models.TextField(verbose_name="Описание")
    requirements = models.TextField(verbose_name="Требования")
    salary = models.CharField(max_length=100, verbose_name="Заработная плата")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Вакансия"
        verbose_name_plural = "Вакансии"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class UserNotification(models.Model):
    """Персональные уведомления для пользователей"""
    
    TYPE_CHOICES = [
        ('order_approved', 'Заказ одобрен'),
        ('order_rejected', 'Заказ отклонен'),
        ('order_cancelled', 'Заказ отменен'),
        ('cancel_approved', 'Отмена одобрена'),
        ('cancel_rejected', 'Отмена отклонена'),
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
        related_name='user_notifications',
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
