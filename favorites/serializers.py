from rest_framework import serializers
from .models import Favorite
from menu.serializers import ProductSerializer


class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = Favorite
        fields = ["id", "product", "created_at"]