from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order_link", "product", "quantity", "price", "total_price")
    list_filter = ("order__status", "order__created_at")
    search_fields = ("order__id", "product__name")
    raw_id_fields = ("order", "product")
    
    def order_link(self, obj):
        if obj.order:
            url = f"/admin/orders/order/{obj.order.id}/change/"
            return format_html('<a href="{}">Заказ #{}</a>', url, obj.order.id)
        return "-"
    order_link.short_description = 'Заказ'
    order_link.admin_order_field = 'order__id'
    
    def total_price(self, obj):
        return obj.total_price
    total_price.short_description = 'Сумма'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ["product"]
    readonly_fields = ('total_price',)
    
    def total_price(self, obj):
        if obj.pk:  # Только для существующих объектов
            return obj.total_price
        return 0
    total_price.short_description = 'Сумма позиции'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user_link", "status_badge", "delivery_type", "created_at", "total_price_format")
    list_filter = ("status", "delivery_type", "created_at")
    search_fields = ("id", "user__first_name", "user__username", "user__telegram_id")
    readonly_fields = ("created_at", "updated_at", "total_price")
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'status', 'delivery_type')
        }),
        ('Адрес доставки', {
            'fields': ('address_text', 'latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Дополнительно', {
            'fields': ('comment', 'created_at', 'updated_at', 'total_price'),
        }),
    )
    
    def user_link(self, obj):
        if obj.user:
            url = f"/admin/telegram_users/telegramuser/{obj.user.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.user)
        return "-"
    user_link.short_description = 'Пользователь'
    user_link.admin_order_field = 'user__first_name'
    
    def status_badge(self, obj):
        status_colors = {
            'cart': 'gray',
            'new': 'blue',
            'preparing': 'orange',
            'delivering': 'purple',
            'done': 'green',
            'canceled': 'red',
        }
        
        status_labels = {
            'cart': 'Корзина',
            'new': 'Новый',
            'preparing': 'Готовится',
            'delivering': 'Доставляется',
            'done': 'Завершён',
            'canceled': 'Отменён',
        }
        
        color = status_colors.get(obj.status, 'gray')
        label = status_labels.get(obj.status, obj.status)
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color, label
        )
    status_badge.short_description = 'Статус'
    status_badge.admin_order_field = 'status'
    
    def total_price_format(self, obj):
        return f'{obj.total_price} сум'
    total_price_format.short_description = 'Сумма'
    total_price_format.admin_order_field = 'total_price'
    
    def total_price(self, obj):
        return f'{obj.total_price} сум'
    total_price.short_description = 'Общая сумма'
