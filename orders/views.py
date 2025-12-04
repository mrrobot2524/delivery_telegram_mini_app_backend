from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from telegram_users.models import TelegramUser
from telegram_users.tma import validate_init_data
from .models import Order, OrderItem
from .serializers import OrderSerializer
from menu.models import Product
# import json
# from urllib.parse import parse_qsl



class MiniAppUserMixin:
    """
    Получаем TelegramUser из initData с безопасной валидацией.
    Ожидает заголовок X-Telegram-Init-Data. [web:354][web:536]
    """

    def _get_telegram_user(self, request):
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        data = validate_init_data(init_data)
        if not data or "user" not in data:
            print("MiniAppUserMixin: invalid init_data, user not found")
            return None

        user_payload = data["user"]
        telegram_id = user_payload.get("id")
        username = user_payload.get("username")
        first_name = user_payload.get("first_name")

        if not telegram_id:
            print("MiniAppUserMixin: no telegram_id in user payload:", user_payload)
            return None

        tg_user, _ = TelegramUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                "username": username,
                "first_name": first_name,
            },
        )
        return tg_user


class DeleteMyOrderView(MiniAppUserMixin, APIView):
    """
    DELETE /api/orders/<int:pk>/delete/
    Удаляет заказ пользователя из истории.
    """

    def delete(self, request, pk):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response(
                {"detail": "Invalid or unknown Telegram user"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = Order.objects.get(id=pk, user=tg_user)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # при желании можно запретить удалять активные заказы, оставив только прошлые
        if order.status in ("new", "preparing", "delivering"):
            return Response(
                {"detail": "Нельзя удалить активный заказ"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class MyOrdersView(MiniAppUserMixin, ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        tg_user = self._get_telegram_user(self.request)
        if not tg_user:
            return Order.objects.none()

        return (
            Order.objects.filter(user=tg_user)
            .exclude(status="cart")
            .order_by("-created_at")[:20]  # последние 20
            .prefetch_related("items__product")
        )

    def list(self, request, *args, **kwargs):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            from rest_framework.response import Response
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)
        return super().list(request, *args, **kwargs)



class CartView(MiniAppUserMixin, APIView):
    """
    GET  /api/orders/cart/       -> текущая корзина + активный заказ (если есть)
    POST /api/orders/cart/       -> добавить товар в корзину
    PATCH /api/orders/cart/      -> обновить delivery_type, address_text, координаты (без оформления)
    """

    def get(self, request):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        # Получаем корзину
        cart = (
            Order.objects.filter(user=tg_user, status="cart")
            .prefetch_related("items__product")
            .first()
        )
        
        # Получаем ВСЕ активные заказы (новые и в работе)
        active_orders = (
            Order.objects.filter(user=tg_user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        response_data = {
            "cart": OrderSerializer(cart).data if cart else {"items": [], "total_price": 0},
            "active_orders": [OrderSerializer(order).data for order in active_orders],
        }
        
        return Response(response_data)

    def post(self, request):
        """
        body: { "product_id": int, "quantity": int? }
        """
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        if not product_id:
            return Response({"detail": "product_id is required"}, status=400)

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=404)

        cart, _ = Order.objects.get_or_create(user=tg_user, status="cart")

        item, created = OrderItem.objects.get_or_create(
            order=cart,
            product=product,
            defaults={"quantity": quantity, "price": product.price},
        )
        if not created:
            item.quantity += quantity
            item.save()

        cart.refresh_from_db()
        
        # Получаем ВСЕ активные заказы
        active_orders = (
            Order.objects.filter(user=tg_user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )
        
        response_data = {
            "cart": OrderSerializer(cart).data,
            "active_orders": [OrderSerializer(order).data for order in active_orders],
        }
        return Response(response_data, status=status.HTTP_200_OK)

    def patch(self, request):
        """
        Обновляет параметры доставки и координаты в корзине (без оформления)
        body: {
          "delivery_type": "pickup" | "delivery",
          "address_text": "...",
          "latitude": 41.3,
          "longitude": 69.2
        }
        """
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        cart = Order.objects.filter(user=tg_user, status="cart").first()
        if not cart:
            return Response({"detail": "Cart not found"}, status=404)

        # Обновляем delivery_type если передан
        delivery_type = request.data.get("delivery_type")
        if delivery_type:
            if delivery_type not in ("pickup", "delivery"):
                return Response(
                    {"detail": "delivery_type must be 'pickup' or 'delivery'"},
                    status=400,
                )
            cart.delivery_type = delivery_type

        # Обновляем address_text если передан
        address_text = request.data.get("address_text")
        if address_text:
            cart.address_text = address_text

        # Обновляем координаты если переданы
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        if latitude is not None:
            try:
                cart.latitude = float(latitude)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "latitude must be a number"}, status=400
                )
        if longitude is not None:
            try:
                cart.longitude = float(longitude)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "longitude must be a number"}, status=400
                )

        cart.save()
        cart.refresh_from_db()
        
        # Получаем ВСЕ активные заказы
        active_orders = (
            Order.objects.filter(user=tg_user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )
        
        response_data = {
            "cart": OrderSerializer(cart).data,
            "active_orders": [OrderSerializer(order).data for order in active_orders],
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class CartItemView(MiniAppUserMixin, APIView):
    """
    PATCH /api/orders/cart/item/
    body: { "item_id": int, "action": "inc" | "dec" }
    """

    def patch(self, request):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        item_id = request.data.get("item_id")
        action = request.data.get("action")

        if action not in ("inc", "dec") or not item_id:
            return Response({"detail": "item_id and action are required"}, status=400)

        try:
            item = OrderItem.objects.select_related("order").get(
                id=item_id,
                order__user=tg_user,
                order__status="cart",
            )
        except OrderItem.DoesNotExist:
            return Response({"detail": "Cart item not found"}, status=404)

        if action == "inc":
            item.quantity += 1
            item.save()
        elif action == "dec":
            if item.quantity > 1:
                item.quantity -= 1
                item.save()
            else:
                # если количество становится 0 — удаляем позицию
                item.delete()

        # обновляем корзину и отдаём целиком
        cart = (
            Order.objects.filter(user=tg_user, status="cart")
            .prefetch_related("items__product")
            .first()
        )
        
        # Получаем ВСЕ активные заказы
        active_orders = (
            Order.objects.filter(user=tg_user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )
        
        response_data = {
            "cart": OrderSerializer(cart).data if cart else {"items": [], "total_price": 0},
            "active_orders": [OrderSerializer(order).data for order in active_orders],
        }
        
        return Response(response_data, status=status.HTTP_200_OK)



class CheckoutView(MiniAppUserMixin, APIView):
    """
    POST /api/orders/checkout/
    Оформление заказа из корзины.
    body:
    {
      "delivery_type": "pickup" | "delivery",
      "address_text": "...",        # опционально
      "latitude": 41.3,             # для доставки
      "longitude": 69.2,
      "comment": "без васаби"       # опционально
    }
    """

    def post(self, request):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        delivery_type = request.data.get("delivery_type")
        address_text = request.data.get("address_text")
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        comment = request.data.get("comment", "")

        if delivery_type not in ("pickup", "delivery"):
            return Response(
                {"detail": "delivery_type must be 'pickup' or 'delivery'"},
                status=400,
            )

        cart = (
            Order.objects.filter(user=tg_user, status="cart")
            .prefetch_related("items__product")
            .first()
        )
        if not cart or not cart.items.exists():
            return Response({"detail": "Cart is empty"}, status=400)

        # Валидация полей для доставки
        if delivery_type == "delivery":
            if not (address_text or (latitude is not None and longitude is not None)):
                return Response(
                    {
                        "detail": "For delivery, provide address_text or latitude+longitude"
                    },
                    status=400,
                )

        # Заполняем заказ
        cart.delivery_type = delivery_type
        cart.address_text = address_text or cart.address_text

        if latitude is not None and longitude is not None:
            try:
                cart.latitude = float(latitude)
                cart.longitude = float(longitude)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "latitude and longitude must be numbers"}, status=400
                )

        cart.comment = comment or cart.comment
        cart.status = "new"  # корзина превращается в оформленный заказ
        cart.save()

        # Получаем новую корзину (пустую) и ВСЕ активные заказы
        new_cart = (
            Order.objects.filter(user=tg_user, status="cart")
            .prefetch_related("items__product")
            .first()
        )
        
        # Получаем ВСЕ активные заказы (включая только что созданный)
        active_orders = (
            Order.objects.filter(user=tg_user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )
        
        response_data = {
            "cart": OrderSerializer(new_cart).data if new_cart else {"items": [], "total_price": 0},
            "active_orders": [OrderSerializer(order).data for order in active_orders],
        }
        return Response(response_data, status=status.HTTP_200_OK)


class CancelOrderView(MiniAppUserMixin, APIView):
    """
    POST /api/orders/cancel_order/
    Отмена всего активного заказа
    body: { "order_id": int }
    """

    def post(self, request):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"detail": "order_id is required"}, status=400)

        try:
            order = Order.objects.get(id=order_id, user=tg_user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)

        # Проверяем что это активный заказ
        if order.status not in ("new", "preparing", "delivering"):
            return Response(
                {"detail": "Can only cancel active orders"}, status=400
            )

        # Меняем статус заказа на отменён
        order.status = "cancelled"
        order.save()

        # Получаем корзину и ВСЕ активные заказы
        cart = (
            Order.objects.filter(user=tg_user, status="cart")
            .prefetch_related("items__product")
            .first()
        )

        # Получаем ВСЕ активные заказы
        active_orders = (
            Order.objects.filter(user=tg_user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        response_data = {
            "cart": OrderSerializer(cart).data if cart else {"items": [], "total_price": 0},
            "active_orders": [OrderSerializer(order).data for order in active_orders],
        }
        return Response(response_data, status=status.HTTP_200_OK)


class UpdateOrderStatusView(MiniAppUserMixin, APIView):
    """
    POST /api/orders/update_status/
    Обновление статуса заказа (для администратора)
    body: { "order_id": int, "status": str }
    """

    def post(self, request):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        # Проверяем права администратора
        if not hasattr(tg_user, 'is_admin') or not tg_user.is_admin:
            return Response({"detail": "Access denied. Admin rights required."}, status=403)

        order_id = request.data.get("order_id")
        new_status = request.data.get("status")
        
        if not order_id or not new_status:
            return Response({"detail": "order_id and status are required"}, status=400)

        # Проверяем, что статус допустимый
        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {"detail": f"Invalid status. Valid statuses: {valid_statuses}"}, 
                status=400
            )

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)

        # Обновляем статус заказа
        old_status = order.status
        order.status = new_status
        order.save()

        # Получаем корзину и ВСЕ активные заказы
        cart = (
            Order.objects.filter(user=order.user, status="cart")
            .prefetch_related("items__product")
            .first()
        )

        # Получаем ВСЕ активные заказы
        active_orders = (
            Order.objects.filter(user=order.user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        response_data = {
            "cart": OrderSerializer(cart).data if cart else {"items": [], "total_price": 0},
            "active_orders": [OrderSerializer(order).data for order in active_orders],
            "message": f"Order status updated from '{old_status}' to '{new_status}'"
        }
        return Response(response_data, status=status.HTTP_200_OK)


class CancelOrderItemView(MiniAppUserMixin, APIView):
    """
    POST /api/orders/cancel_item/
    Отмена конкретного товара в активном заказе
    body: { "order_item_id": int }
    """

    def post(self, request):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        order_item_id = request.data.get("order_item_id")
        if not order_item_id:
            return Response({"detail": "order_item_id is required"}, status=400)

        try:
            order_item = OrderItem.objects.get(id=order_item_id)
        except OrderItem.DoesNotExist:
            return Response({"detail": "Order item not found"}, status=404)

        # Проверяем что заказ принадлежит пользователю
        if order_item.order.user != tg_user:
            return Response({"detail": "Unauthorized"}, status=403)

        # Проверяем что это активный заказ
        if order_item.order.status not in ("new", "preparing", "delivering"):
            return Response(
                {"detail": "Can only cancel items from active orders"}, status=400
            )

        order_item.delete()

        # Получаем корзину и ВСЕ активные заказы
        cart = (
            Order.objects.filter(user=tg_user, status="cart")
            .prefetch_related("items__product")
            .first()
        )

        # Получаем ВСЕ активные заказы
        active_orders = (
            Order.objects.filter(user=tg_user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        response_data = {
            "cart": OrderSerializer(cart).data if cart else {"items": [], "total_price": 0},
            "active_orders": [OrderSerializer(order).data for order in active_orders],
        }
        return Response(response_data, status=status.HTTP_200_OK)
