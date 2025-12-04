from rest_framework.generics import ListAPIView
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryListView(ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer


class ProductListView(ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True)
        category_id = self.request.query_params.get("category_id")
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs
