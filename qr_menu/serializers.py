from rest_framework import serializers
from .models import QROnlyCategory, QROnlyProduct

class QROnlyProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = QROnlyProduct
        fields = ["id", "name", "description", "price", "image", "is_active"]

class QROnlyCategorySerializer(serializers.ModelSerializer):
    products = QROnlyProductSerializer(many=True, read_only=True)
    
    class Meta:
        model = QROnlyCategory
        fields = ["id", "name", "image", "is_active", "products"]
