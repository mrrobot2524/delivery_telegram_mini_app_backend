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
    
    # Новые поля для акций
    discounted_price = serializers.SerializerMethodField()
    has_promotion = serializers.SerializerMethodField()
    promotion_info = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "price", 
            "discounted_price",  # новое поле
            "has_promotion",     # новое поле
            "promotion_info",    # новое поле
            "image", "category", "is_active"
        ]
    
    def get_image(self, obj):
        if obj.image:
            # Возвращаем относительный URL - фронтенд добавит базовый URL
            return obj.image.url
        return None
    
    def get_discounted_price(self, obj):
        """Цена с учетом акции"""
        return obj.get_discounted_price()
    
    def get_has_promotion(self, obj):
        """Есть ли активная акция"""
        return obj.get_active_promotion() is not None
    
    def get_promotion_info(self, obj):
        """Информация об акции"""
        promo = obj.get_active_promotion()
        if not promo:
            return None
        
        return {
            "name": promo.name,
            "discount_type": promo.discount_type,
            "discount_value": float(promo.discount_value),
        }
