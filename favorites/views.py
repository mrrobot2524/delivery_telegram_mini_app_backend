from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from telegram_users.models import TelegramUser
from telegram_users.tma import validate_init_data
from menu.models import Product
from .models import Favorite
from .serializers import FavoriteSerializer


class MiniAppUserMixin:
    """
    Получаем TelegramUser из initData с безопасной валидацией.
    Ожидает заголовок X-Telegram-Init-Data.
    """
    
    def _get_telegram_user(self, request):
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        
        # Development mode support
        if init_data == "dev_mode":
            tg_user, _ = TelegramUser.objects.get_or_create(
                telegram_id=999999999,
                defaults={
                    "username": "dev_user",
                    "first_name": "Development",
                    "last_name": "User",
                },
            )
            return tg_user
        
        data = validate_init_data(init_data)
        if not data or "user" not in data:
            print("MiniAppUserMixin: invalid init_data, user not found")
            return None
            
        user_payload = data["user"]
        telegram_id = user_payload.get("id")
        username = user_payload.get("username")
        first_name = user_payload.get("first_name")
        
        if not telegram_id:
            print("MiniAppUserMixin: no telegram_id in user payload:", user_payload)
            return None
            
        tg_user, _ = TelegramUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                "username": username,
                "first_name": first_name,
            },
        )
        return tg_user


class ToggleFavoriteView(MiniAppUserMixin, APIView):
    """
    POST /api/favorites/toggle/
    Переключает состояние избранного для товара
    body: { "product_id": int }
    """
    
    def post(self, request):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)
            
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"detail": "product_id is required"}, status=400)
            
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=404)
            
        # Проверяем, есть ли уже в избранном
        favorite, created = Favorite.objects.get_or_create(
            user=tg_user,
            product=product
        )
        
        # Если уже было в избранном, удаляем
        if not created:
            favorite.delete()
            return Response({"favorited": False, "message": "Removed from favorites"})
            
        # Если добавили в избранное
        return Response({"favorited": True, "message": "Added to favorites"})


class FavoritesListView(MiniAppUserMixin, APIView):
    """
    GET /api/favorites/
    Возвращает список избранных товаров пользователя
    """
    
    def get(self, request):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)
            
        favorites = Favorite.objects.filter(user=tg_user).select_related('product__category')
        serializer = FavoriteSerializer(favorites, many=True)
        
        return Response({
            "favorites": serializer.data
        })