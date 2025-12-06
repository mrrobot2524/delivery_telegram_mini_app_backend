"""
Utility functions for promo codes and orders
"""
from decimal import Decimal
from django.utils import timezone
from .models import PromoCode, Order


def create_promo_code(code, discount_type, discount_value, **kwargs):
    """
    Удобная функция для создания промокода
    
    Args:
        code: Код промокода
        discount_type: 'percentage' или 'fixed'
        discount_value: Значение скидки
        **kwargs: Дополнительные параметры (min_order_amount, max_uses, valid_from, valid_until)
    
    Returns:
        PromoCode instance
    """
    from datetime import timedelta
    
    defaults = {
        'min_order_amount': kwargs.get('min_order_amount', 0),
        'max_uses': kwargs.get('max_uses', 1000),
        'valid_from': kwargs.get('valid_from', timezone.now()),
        'valid_until': kwargs.get('valid_until', timezone.now() + timedelta(days=30)),
        'is_active': kwargs.get('is_active', True),
    }
    
    return PromoCode.objects.create(
        code=code,
        discount_type=discount_type,
        discount_value=discount_value,
        **defaults
    )


def get_active_promo_codes():
    """Получить все активные промокоды"""
    return PromoCode.objects.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_until__gte=timezone.now()
    ).exclude(
        current_uses__gte=models.F('max_uses')
    )


def calculate_order_total(order):
    """
    Пересчитать итоговую сумму заказа
    
    Args:
        order: Order instance
    
    Returns:
        dict with total_price and final_price
    """
    total = sum(
        item.total_price 
        for item in order.items.filter(is_canceled=False)
    )
    
    final = max(total - order.discount_amount, 0)
    
    return {
        'total_price': total,
        'final_price': final,
        'discount_amount': order.discount_amount
    }


def get_order_statistics(user=None):
    """
    Получить статистику заказов
    
    Args:
        user: TelegramUser instance (опционально)
    
    Returns:
        dict with statistics
    """
    from django.db.models import Count, Sum, Avg
    
    queryset = Order.objects.all()
    if user:
        queryset = queryset.filter(user=user)
    
    stats = queryset.aggregate(
        total_orders=Count('id'),
        total_revenue=Sum('discount_amount'),
        avg_order_value=Avg('discount_amount'),
        orders_with_promo=Count('id', filter=models.Q(promo_code__isnull=False))
    )
    
    return stats


def is_restaurant_open():
    """
    Проверка времени работы ресторана (10:00 - 23:00)
    """
    now = timezone.localtime(timezone.now())
    # Время работы: с 10:00 до 23:00
    if 10 <= now.hour < 23:
        return True, "Мы открыты"
    return False, "Ресторан закрыт. Мы работаем с 10:00 до 23:00"
