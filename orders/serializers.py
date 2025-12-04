from rest_framework import serializers
from .models import Order, OrderItem
from menu.serializers import ProductSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "price", "total_price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "delivery_type",
            "address_text",
            "latitude",
            "longitude",
            "comment",
            "created_at",
            "updated_at",
            "total_price",
            "items",
        ]
