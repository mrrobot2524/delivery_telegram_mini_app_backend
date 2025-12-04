from django.urls import path
from .views import CartView, CheckoutView, CartItemView, DeleteMyOrderView, MyOrdersView, CancelOrderItemView, CancelOrderView, UpdateOrderStatusView

urlpatterns = [
    path("cart/", CartView.as_view()),
    path("cart/item/", CartItemView.as_view()),
    path("checkout/", CheckoutView.as_view()),
    path("cancel_item/", CancelOrderItemView.as_view()),
    path("cancel_order/", CancelOrderView.as_view()),
    path("update_status/", UpdateOrderStatusView.as_view()),
    path("my/", MyOrdersView.as_view()),
    path("<int:pk>/delete/", DeleteMyOrderView.as_view()),
]
