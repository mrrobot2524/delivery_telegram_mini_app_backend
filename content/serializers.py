from rest_framework import serializers
from .models import ContentPage, Branch, Promotion, Vacancy, Notification


class NotificationSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'image', 'created_at']
    
    def get_image(self, obj):
        if obj.image:
            # Возвращаем относительный URL - фронтенд добавит базовый URL
            return obj.image.url
        return None


class ContentPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentPage
        fields = '__all__'


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'


class PromotionSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = Promotion
        fields = '__all__'
    
    def get_image(self, obj):
        if obj.image:
            # Возвращаем относительный URL - фронтенд добавит базовый URL
            return obj.image.url
        return None


class VacancySerializer(serializers.ModelSerializer):
    class Meta:
        model = Vacancy
        fields = '__all__'