from rest_framework import serializers
from .models import TelegramUser


class MiniAppAuthSerializer(serializers.Serializer):
    init_data = serializers.CharField()


class TelegramUserSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TelegramUser
        fields = [
            "id",
            "telegram_id",
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "photo_url",
            "is_admin",
            "created_at",
        ]
    
    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None
