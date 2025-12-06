from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from telegram_users.tma import validate_init_data
from telegram_users.models import TelegramUser
from .models import UserAddress
from .serializers import UserAddressSerializer


class MiniAppUserMixin:
    """Получаем TelegramUser из initData с безопасной валидацией"""

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
            return None

        user_payload = data["user"]
        telegram_id = user_payload.get("id")
        username = user_payload.get("username")
        first_name = user_payload.get("first_name")

        if not telegram_id:
            return None

        tg_user, _ = TelegramUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                "username": username,
                "first_name": first_name,
            },
        )
        return tg_user


class UserAddressListCreateView(MiniAppUserMixin, ListCreateAPIView):
    """
    GET /api/addresses/ - список адресов пользователя
    POST /api/addresses/ - создание нового адреса
    """
    serializer_class = UserAddressSerializer

    def get_queryset(self):
        tg_user = self._get_telegram_user(self.request)
        if not tg_user:
            return UserAddress.objects.none()
        return UserAddress.objects.filter(user=tg_user)

    def list(self, request, *args, **kwargs):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response(
                {"detail": "Invalid or unknown Telegram user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response(
                {"detail": "Invalid or unknown Telegram user"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=tg_user)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserAddressDetailView(MiniAppUserMixin, RetrieveUpdateDestroyAPIView):
    """
    GET /api/addresses/<id>/ - получение адреса
    PUT/PATCH /api/addresses/<id>/ - обновление адреса
    DELETE /api/addresses/<id>/ - удаление адреса
    """
    serializer_class = UserAddressSerializer

    def get_queryset(self):
        tg_user = self._get_telegram_user(self.request)
        if not tg_user:
            return UserAddress.objects.none()
        return UserAddress.objects.filter(user=tg_user)

    def retrieve(self, request, *args, **kwargs):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response(
                {"detail": "Invalid or unknown Telegram user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response(
                {"detail": "Invalid or unknown Telegram user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response(
                {"detail": "Invalid or unknown Telegram user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


class SetDefaultAddressView(MiniAppUserMixin, APIView):
    """
    POST /api/addresses/<id>/set-default/
    Установка адреса по умолчанию
    """

    def post(self, request, pk):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response(
                {"detail": "Invalid or unknown Telegram user"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            address = UserAddress.objects.get(id=pk, user=tg_user)
        except UserAddress.DoesNotExist:
            return Response(
                {"detail": "Address not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Снимаем флаг default со всех адресов пользователя
        UserAddress.objects.filter(user=tg_user).update(is_default=False)
        
        # Устанавливаем текущий адрес как default
        address.is_default = True
        address.save()

        serializer = UserAddressSerializer(address)
        return Response(serializer.data, status=status.HTTP_200_OK)
