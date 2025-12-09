from rest_framework import serializers
from .models import Order, OrderItem, PromoCode, Promotion, OrderItemCancellationRequest
from menu.serializers import ProductSerializer
from qr_menu.serializers import QROnlyProductSerializer


class PromoCodeSerializer(serializers.ModelSerializer):
    """Сериализатор для промокодов"""
    class Meta:
        model = PromoCode
        fields = [
            "id",
            "code",
            "discount_type",
            "discount_value",
            "min_order_amount",
            "is_active",
        ]
        read_only_fields = ["id"]


class PromotionSerializer(serializers.ModelSerializer):
    """Сериализатор для акций"""
    products = ProductSerializer(many=True, read_only=True)
    
    class Meta:
        model = Promotion
        fields = [
            "id",
            "name",
            "description",
            "discount_type",
            "discount_value",
            "products",
            "valid_from",
            "valid_until",
            "is_active",
        ]
        read_only_fields = ["id"]


class OrderItemCancellationRequestSerializer(serializers.ModelSerializer):
    """Сериализатор для запросов на отмену товара"""
    requested_by_name = serializers.CharField(source="requested_by.first_name", read_only=True)
    processed_by_name = serializers.CharField(source="processed_by.first_name", read_only=True)
    
    class Meta:
        model = OrderItemCancellationRequest
        fields = [
            "id",
            "order_item",
            "requested_by",
            "requested_by_name",
            "status",
            "reason",
            "requested_at",
            "processed_by",
            "processed_by_name",
            "processed_at",
        ]

class OrderCancellationRequestSerializer(serializers.ModelSerializer):
    """Сериализатор для запросов на отмену заказа"""
    requested_by_name = serializers.CharField(source="requested_by.first_name", read_only=True)
    processed_by_name = serializers.CharField(source="processed_by.first_name", read_only=True)
    
    class Meta:
        from .models import OrderCancellationRequest
        model = OrderCancellationRequest
        fields = [
            "id",
            "order",
            "requested_by",
            "requested_by_name",
            "status",
            "reason",
            "requested_at",
            "processed_by",
            "processed_by_name",
            "processed_at",
        ]
        read_only_fields = ["id", "requested_at", "processed_at", "requested_by_name", "processed_by_name"]



class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    qr_product = QROnlyProductSerializer(read_only=True)
    cancellation_request = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "qr_product",
            "quantity",
            "price",
            "total_price",
            "is_canceled",
            "canceled_at",
            "cancellation_request",
        ]

    def get_cancellation_request(self, obj):
        """Получить последний запрос на отмену"""
        # Возвращаем последний запрос независимо от статуса
        request = obj.cancellation_requests.order_by("-requested_at").first()
        if request:
            return OrderItemCancellationRequestSerializer(request).data
        return None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    promo_code_info = PromoCodeSerializer(source="promo_code", read_only=True)
    cancellation_request = serializers.SerializerMethodField()
    
    def get_cancellation_request(self, obj):
        # Возвращаем последний запрос
        request = obj.cancellation_requests.order_by("-requested_at").first()
        if request:
            return OrderCancellationRequestSerializer(request).data
        return None

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
            "discount_amount",
            "final_price",
            "promo_code",
            "promo_code_info",
            "estimated_time",
            "payment_method",
            "payment_status",
            "paid_at",
            "items",
            "cancellation_request",
        ]
        read_only_fields = ["total_price", "final_price"]
