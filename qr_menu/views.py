from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import QRTable, QROnlyCategory, QROnlyProduct
from .serializers import QROnlyCategorySerializer, QROnlyProductSerializer

class QRMenuDataView(APIView):
    """
    GET /api/qr-menu/<table_uuid>/
    Возвращает список категорий и продуктов, доступных для конкретного стола.
    В старых версиях мы фильтровали через параметры, теперь это отдельное независимое API.
    """
    permission_classes = [] # Public access

    def get(self, request, table_uuid):
        # 1. Находим стол
        table = get_object_or_404(QRTable, uuid=table_uuid)
        
        # 2. Получаем категории
        # Аккуратно: если у стола нет привязанных категорий, 
        # показываем ВСЕ активные категории QR-меню (fallback), 
        # чтобы меню не было пустым по ошибке.
        if table.categories.exists():
            categories = table.categories.filter(is_active=True)
        else:
            categories = QROnlyCategory.objects.filter(is_active=True)
            
        categories = categories.prefetch_related("products").order_by("sort_order")
        
        # 3. Сериализуем
        data = QROnlyCategorySerializer(categories, many=True, context={"request": request}).data
        
        return Response({
            "table_number": table.number,
            "categories": data
        })

class QRProductDetailView(APIView):
    """
    GET /api/qr-menu/products/<id>/
    """
    permission_classes = []

    def get(self, request, pk):
        product = get_object_or_404(QROnlyProduct, pk=pk, is_active=True)
        return Response(QROnlyProductSerializer(product).data)
