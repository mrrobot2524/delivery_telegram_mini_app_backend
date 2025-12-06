from django.urls import path
from .views import (
    CartView,
    CheckoutView,
    CartItemView,
    DeleteMyOrderView,
    MyOrdersView,
    CancelOrderItemView,
    CancelOrderView,
    UpdateOrderStatusView,
    ValidatePromoCodeView,
    ApplyPromoCodeView,
    RequestCancelOrderItemView,
    ProcessCancellationRequestView,
    PollOrderStatusView,
    InitiatePaymentView,
    PaymentCallbackView,
    CheckPaymentStatusView,
    MockPaymentCallbackView,
)

urlpatterns = [
    # Корзина
    path("cart/", CartView.as_view()),
    path("cart/item/", CartItemView.as_view()),
    path("checkout/", CheckoutView.as_view()),
    
    # Заказы
    path("my/", MyOrdersView.as_view()),
    path("<int:pk>/delete/", DeleteMyOrderView.as_view()),
    path("poll/<int:order_id>/", PollOrderStatusView.as_view(), name="poll_order_status"), # Added poll endpoint
    
    # Отмена заказов и товаров
    path("cancel_item/", CancelOrderItemView.as_view()),  # Прямая отмена (старый метод)
    path("cancel_order/", CancelOrderView.as_view()),
    path("request-cancel-item/", RequestCancelOrderItemView.as_view(), name="request_cancel_item"), # Added name
    path("process-cancellation/", ProcessCancellationRequestView.as_view(), name="process_cancellation"), # Added name
    
    # Промокоды
    path("validate-promo/", ValidatePromoCodeView.as_view(), name="validate_promo_code"), # Added name
    path("apply-promo/", ApplyPromoCodeView.as_view(), name="apply_promo_code"), # Added name
    
    # Онлайн оплата
    path("initiate-payment/", InitiatePaymentView.as_view(), name="initiate_payment"),
    path("payment-callback/", PaymentCallbackView.as_view(), name="payment_callback"),
    path("payment/mock-callback/", MockPaymentCallbackView.as_view(), name="mock_payment_callback"),
    path("payment-status/<int:order_id>/", CheckPaymentStatusView.as_view(), name="check_payment_status"),
    
    # Админ/оператор
    path("update_status/", UpdateOrderStatusView.as_view()),
]
