from rest_framework.generics import ListAPIView
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryListView(ListAPIView):
    serializer_class = CategorySerializer

    def get_queryset(self):
        qs = Category.objects.filter(is_active=True)
    def get_queryset(self):
        qs = Category.objects.filter(is_active=True)
        
        # Table specific filter
        table_uuid = self.request.query_params.get("table_uuid")
        if table_uuid:
            # If table is specified, we ONLY show categories linked to this table
            # However, if table has no specific categories linked, we might show all?
            # User requirement: "categories... belong to table".
            # Let's enforce linkage.
            qs = qs.filter(tables__uuid=table_uuid)
            return qs

        # Check source (Guest/App) fallback
        is_guest = self.request.headers.get("X-Guest-ID")
        if is_guest:
            # General QR fallback if table_uuid not sent, but for QR setup usually table is known via URL
            return qs.filter(is_for_qr=True)
            
        return qs.filter(is_for_app=True)


class ProductListView(ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True)
        
        # Table specific filter
        table_uuid = self.request.query_params.get("table_uuid")
        if table_uuid:
             qs = qs.filter(category__tables__uuid=table_uuid)
        else:
            # Check source fallback
            is_guest = self.request.headers.get("X-Guest-ID")
            if is_guest:
                qs = qs.filter(is_for_qr=True)
            else:
                qs = qs.filter(is_for_app=True)
        category_id = self.request.query_params.get("category_id")
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs
