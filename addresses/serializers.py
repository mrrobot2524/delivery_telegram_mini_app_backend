from rest_framework import serializers
from .models import UserAddress


class UserAddressSerializer(serializers.ModelSerializer):
    """Сериализатор для адресов пользователя"""
    
    class Meta:
        model = UserAddress
        fields = [
            "id",
            "title",
            "address_text",
            "latitude",
            "longitude",
            "entrance",
            "floor",
            "apartment",
            "intercom",
            "comment",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):
        """Валидация данных адреса"""
        # Проверяем что указан либо текстовый адрес, либо координаты
        if not data.get("address_text") and not (data.get("latitude") and data.get("longitude")):
            raise serializers.ValidationError(
                "Необходимо указать либо текстовый адрес, либо координаты"
            )
        return data
