"""
Utility functions for promo codes and orders
"""
from decimal import Decimal
import math
from django.db import models
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
    Проверка времени работы ресторана (через настройки в БД)
    """
    # Local import to avoid circular dependency
    from .models import RestaurantSettings

    # Получаем настройки (или создаем дефолтные при первом вызове)
    settings, _ = RestaurantSettings.objects.get_or_create(pk=1)

    # Ручной режим
    if settings.is_manual_mode:
        if settings.is_open_manual:
             return True, "Мы открыты"
        else:
             return False, settings.closed_message

    now = timezone.localtime(timezone.now()).time()

    # Проверка интервала
    # Если время открытия < времени закрытия (например 10:00 - 23:00)
    if settings.opening_time < settings.closing_time:
        is_open = settings.opening_time <= now <= settings.closing_time
    else:
        # Ресторан работает через полночь (например 18:00 - 02:00)
        is_open = now >= settings.opening_time or now <= settings.closing_time

    if is_open:
        return True, "Мы открыты"
    
    return False, settings.closed_message

def get_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Вычисляет расстояние между двумя точками (в км).
    """
    R = 6371  # Радиус Земли в км
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) * math.sin(d_lat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) * math.sin(d_lon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_delivery_cost(user_lat, user_lng):
    """
    Расчет стоимости доставки на основе координат.
    Возвращает (cost, distance_km)
    """
    from .models import RestaurantSettings
    settings, _ = RestaurantSettings.objects.get_or_create(pk=1)
    
    # Если координаты не переданы или 0, возвращаем базовую
    if not user_lat or not user_lng:
        return settings.delivery_base_price, 0.0
    
    dist = get_haversine_distance(
        settings.restaurant_lat, settings.restaurant_lng,
        user_lat, user_lng
    )
    
    # Округляем расстояние до 1 знака после запятой для удобства
    dist_display = round(dist, 1)

    if dist <= settings.delivery_base_km:
        return settings.delivery_base_price, dist_display
    
    # Если расстояние больше базового
    extra_km = dist - settings.delivery_base_km
    extra_cost = Decimal(extra_km) * settings.delivery_price_per_km
    
    total_cost = settings.delivery_base_price + extra_cost
    
    # Округляем цену до 100 сум
    # Например: 15432 -> 15500 (ceil)
    total_cost = math.ceil(total_cost / 100) * 100
    
    return Decimal(total_cost), dist_display
