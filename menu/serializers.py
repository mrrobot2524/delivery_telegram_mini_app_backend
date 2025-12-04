from rest_framework import serializers
from django.urls import reverse
from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "is_active"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "image", "category", "is_active"]
    
    def get_image(self, obj):
        if obj.image:
            # Возвращаем относительный URL - фронтенд добавит базовый URL
            return obj.image.url
        return None
