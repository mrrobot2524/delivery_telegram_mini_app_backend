from django.urls import path
from .views import QRMenuDataView, QRProductDetailView

urlpatterns = [
    path("table/<uuid:table_uuid>/", QRMenuDataView.as_view(), name="qr_menu_table"),
    path("products/<int:pk>/", QRProductDetailView.as_view(), name="qr_product_detail"),
]
