# 📋 План реализации системы персональных уведомлений

**Дата:** 2025-12-08  
**Время:** 18:12

---

## 🎯 Цель:

Создать систему персональных уведомлений, чтобы уведомления об отказе или одобрении заказов отображались в NotificationsModal внутри приложения, а не отправлялись только в Telegram бот.

---

## 📝 Что нужно сделать:

### **1. Backend (Django):**

#### 1.1. Создать модель `UserNotification`

**Файл:** `/Users/mac/Documents/NextJs_projects/ky_sushi/content/models.py`

```python
class UserNotification(models.Model):
    """Персональные уведомления для пользователей"""
    
    TYPE_CHOICES = [
        ('order_approved', 'Заказ одобрен'),
        ('order_rejected', 'Заказ отклонен'),
        ('order_cancelled', 'Заказ отменен'),
        ('order_status', 'Статус заказа'),
        ('promo', 'Акция'),
        ('info', 'Информация'),
    ]
    
    telegram_id = models.BigIntegerField(verbose_name="Telegram ID", db_index=True)
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
```

#### 1.2. Создать сериализатор

**Файл:** `/Users/mac/Documents/NextJs_projects/ky_sushi/content/serializers.py`

```python
class UserNotificationSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = UserNotification
        fields = ['id', 'title', 'message', 'notification_type', 'order', 'order_number', 'is_read', 'created_at']
```

#### 1.3. Создать API endpoint

**Файл:** `/Users/mac/Documents/NextJs_projects/ky_sushi/content/views.py`

```python
class UserNotificationListView(ListAPIView):
    """API для получения персональных уведомлений пользователя"""
    serializer_class = UserNotificationSerializer
    
    def get_queryset(self):
        telegram_id = self.request.data.get('telegram_id') or \
                     self.request.query_params.get('telegram_id')
        
        if not telegram_id:
            return UserNotification.objects.none()
        
        return UserNotification.objects.filter(
            telegram_id=telegram_id
        ).select_related('order')[:50]  # Последние 50 уведомлений
```

**Добавить в urls.py:**
```python
path('user-notifications/', UserNotificationListView.as_view(), name='user-notifications'),
```

#### 1.4. Создать функцию для создания уведомлений

**Файл:** `/Users/mac/Documents/NextJs_projects/ky_sushi/content/utils.py` (новый файл)

```python
from .models import UserNotification

def create_user_notification(telegram_id, title, message, notification_type='info', order=None):
    """Создать персональное уведомление для пользователя"""
    return UserNotification.objects.create(
        telegram_id=telegram_id,
        title=title,
        message=message,
        notification_type=notification_type,
        order=order
    )
```

#### 1.5. Интегрировать с сигналами заказов

**Файл:** `/Users/mac/Documents/NextJs_projects/ky_sushi/orders/signals.py` (создать если нет)

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, CancellationRequest
from content.utils import create_user_notification

@receiver(post_save, sender=CancellationRequest)
def notify_cancellation_status(sender, instance, created, **kwargs):
    """Уведомление при изменении статуса запроса на отмену"""
    if not created and instance.status in ['approved', 'rejected']:
        order = instance.order
        
        if instance.status == 'approved':
            title = "Заказ отменен"
            message = f"Ваш заказ #{order.order_number} был отменен"
            notification_type = 'order_cancelled'
        else:  # rejected
            title = "Отказ в отмене"
            message = f"Запрос на отмену заказа #{order.order_number} был отклонен"
            notification_type = 'order_rejected'
        
        create_user_notification(
            telegram_id=order.telegram_id,
            title=title,
            message=message,
            notification_type=notification_type,
            order=order
        )

@receiver(post_save, sender=Order)
def notify_order_status(sender, instance, created, **kwargs):
    """Уведомление при изменении статуса заказа"""
    if not created:
        # Можно добавить уведомления при изменении статуса
        pass
```

#### 1.6. Зарегистрировать в админке

**Файл:** `/Users/mac/Documents/NextJs_projects/ky_sushi/content/admin.py`

```python
@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'telegram_id', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'telegram_id']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
```

---

### **2. Frontend (React):**

#### 2.1. Обновить API клиент

**Файл:** `/Users/mac/Documents/NextJs_projects/ky_sushi_front/src/api/client.js`

Добавить функцию для получения персональных уведомлений:

```javascript
export async function fetchUserNotifications(initData) {
  return apiFetch('/api/content/user-notifications/', { initData });
}
```

#### 2.2. Обновить NotificationsModal

**Файл:** `/Users/mac/Documents/NextJs_projects/ky_sushi_front/src/components/NotificationsModal.jsx`

- Изменить API endpoint с `/api/content/notifications/` на `/api/content/user-notifications/`
- Обновить отображение уведомлений с учетом новых типов
- Добавить иконки для разных типов уведомлений

---

## 🔄 Порядок выполнения:

1. ✅ Создать модель `UserNotification` в `content/models.py`
2. ✅ Создать миграцию: `python manage.py makemigrations`
3. ✅ Применить миграцию: `python manage.py migrate`
4. ✅ Создать сериализатор в `content/serializers.py`
5. ✅ Создать view в `content/views.py`
6. ✅ Добавить URL в `content/urls.py`
7. ✅ Создать утилиту в `content/utils.py`
8. ✅ Создать сигналы в `orders/signals.py`
9. ✅ Зарегистрировать сигналы в `orders/apps.py`
10. ✅ Зарегистрировать в админке
11. ✅ Обновить frontend API
12. ✅ Обновить NotificationsModal
13. ✅ Тестирование

---

## 📌 Примечания:

- Старая модель `Notification` остается для глобальных уведомлений
- Новая модель `UserNotification` для персональных уведомлений
- Уведомления создаются автоматически при изменении статуса заказа/отмены
- Пользователь видит только свои уведомления

---

**Готово к реализации!** 🚀
