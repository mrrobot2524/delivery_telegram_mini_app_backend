import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import TelegramUser
from .serializers import MiniAppAuthSerializer, TelegramUserSerializer
from .tma import validate_init_data
from orders.models import Order
from orders.serializers import OrderSerializer
from favorites.models import Favorite

class MiniAppAuthView(APIView):
    authentication_classes = []  # AllowAny
    permission_classes = []

    def post(self, request):
        serializer = MiniAppAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        init_data = serializer.validated_data["init_data"]

        data = validate_init_data(init_data)
        if not data or "user" not in data:
            return Response({"detail": "Invalid init data"}, status=status.HTTP_400_BAD_REQUEST)

        user_payload = data["user"]
        telegram_id = user_payload["id"]
        username = user_payload.get("username")
        first_name = user_payload.get("first_name")
        last_name = user_payload.get("last_name")

        tg_user, _ = TelegramUser.objects.update_or_create(
            telegram_id=telegram_id,
            defaults={
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
            },
        )

        return Response(
            {
                "telegram_id": tg_user.telegram_id,
                "username": tg_user.username,
                "first_name": tg_user.first_name,
                "last_name": tg_user.last_name,
            }
        )


class UserProfileView(APIView):
    permission_classes = []  # AllowAny

    def get(self, request):
        # Получаем init_data из заголовка
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        
        data = validate_init_data(init_data)
        if not data or "user" not in data:
            return Response({"detail": "Invalid init data"}, status=status.HTTP_400_BAD_REQUEST)

        user_payload = data["user"]
        telegram_id = user_payload["id"]
        
        try:
            tg_user = TelegramUser.objects.get(telegram_id=telegram_id)
            
            # Получаем статистику пользователя
            orders_count = Order.objects.filter(user=tg_user).exclude(status='cart').count()
            favorites_count = Favorite.objects.filter(user=tg_user).count()
            
            # Получаем историю заказов (последние 20)
            orders_history = (
                Order.objects.filter(user=tg_user)
                .exclude(status='cart')
                .order_by('-created_at')[:20]
                .prefetch_related('items__product')
            )
            
            # Получаем активные заказы
            active_orders = (
                Order.objects.filter(user=tg_user, status__in=['new', 'preparing', 'delivering'])
                .order_by('-created_at')
                .prefetch_related('items__product')
            )
            
            # Сериализуем данные пользователя
            user_serializer = TelegramUserSerializer(tg_user, context={'request': request})
            user_data = user_serializer.data
            
            # Добавляем статистику и заказы
            user_data['stats'] = {
                'orders_count': orders_count,
                'favorites_count': favorites_count
            }
            user_data['orders_history'] = OrderSerializer(orders_history, many=True).data
            user_data['active_orders'] = OrderSerializer(active_orders, many=True).data
            
            return Response(user_data)
        except TelegramUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)