from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework import parsers
from decimal import Decimal
from django.utils import timezone
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
        
        # Development mode support
        if init_data == "dev_mode":
            print("MiniAppUserMixin: Using development mode")
            # Создаем или получаем тестового пользователя
            tg_user, created = TelegramUser.objects.get_or_create(
                telegram_id=999999999,  # Test user ID
                defaults={
                    "username": "dev_user",
                    "first_name": "Development",
                    "last_name": "User",
                },
            )
            if created:
                print(f"Created dev user: {tg_user}")
            return tg_user
        # Guest User Support
        guest_id = request.headers.get("X-Guest-ID")
        if not init_data and guest_id:
             try:
                # Guest IDs are negative to avoid conflict with Telegram IDs
                g_id = int(guest_id)
                if g_id > 0: g_id = -g_id # Force negative
                
                tg_user, created = TelegramUser.objects.get_or_create(
                    telegram_id=g_id,
                    defaults={
                        "username": f"guest_{abs(g_id)}",
                        "first_name": "Гость",
                        "last_name": "",
                    },
                )
                return tg_user
             except ValueError:
                 pass

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
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

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
            .prefetch_related(
                "items__product",
                "cancellation_requests",
                "items__cancellation_requests"
            )
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
        qr_product_id = request.data.get("qr_product_id")
        quantity = int(request.data.get("quantity", 1))

        if not product_id and not qr_product_id:
            return Response({"detail": "product_id or qr_product_id is required"}, status=400)

        target_product = None
        target_qr_product = None
        price = 0
        
        if product_id:
            try:
                target_product = Product.objects.get(id=product_id, is_active=True)
                price = target_product.get_discounted_price()
            except Product.DoesNotExist:
                return Response({"detail": "Product not found"}, status=404)
        
        elif qr_product_id:
            from qr_menu.models import QROnlyProduct
            try:
                target_qr_product = QROnlyProduct.objects.get(id=qr_product_id, is_active=True)
                price = target_qr_product.price
            except QROnlyProduct.DoesNotExist:
                return Response({"detail": "QR Product not found"}, status=404)

        cart, _ = Order.objects.get_or_create(user=tg_user, status="cart")

        # Ищем существующий item
        # get_or_create может быть сложноват с разными полями, сделаем явно
        item_qs = OrderItem.objects.filter(order=cart)
        if target_product:
            item_qs = item_qs.filter(product=target_product)
        else:
            item_qs = item_qs.filter(qr_product=target_qr_product)
            
        item = item_qs.first()

        if item:
            item.quantity += quantity
            item.price = price
            item.save()
        else:
            item = OrderItem.objects.create(
                order=cart,
                product=target_product,
                qr_product=target_qr_product,
                quantity=quantity,
                price=price
            )

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
          "longitude": 69.2,
          "address_id": 123     # Можно передать ID сохраненного адреса
        }
        """
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        # Парсим JSON данные, если они пришли как строка
        data = request.data
        if isinstance(data, str):
            try:
                import json
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return Response({"detail": "Invalid JSON data"}, status=400)

        cart = Order.objects.filter(user=tg_user, status="cart").first()
        if not cart:
            return Response({"detail": "Cart not found"}, status=404)

        # Обновляем delivery_type если передан
        delivery_type = data.get("delivery_type")
        if delivery_type:
            if delivery_type not in ("pickup", "delivery"):
                return Response(
                    {"detail": "delivery_type must be 'pickup' or 'delivery'"},
                    status=400,
                )
            cart.delivery_type = delivery_type

        # Если передан address_id, пытаемся найти адрес и заполнить поля
        address_id = data.get("address_id")
        if address_id:
            from addresses.models import UserAddress
            try:
                user_address = UserAddress.objects.get(id=address_id, user=tg_user)
                cart.address_text = user_address.address_text
                
                # Собираем доп. инфо в комментарий или адрес, если нужно
                # Но пока просто координаты
                if user_address.latitude and user_address.longitude:
                    cart.latitude = user_address.latitude
                    cart.longitude = user_address.longitude
            except UserAddress.DoesNotExist:
                return Response({"detail": "Address not found"}, status=404)
        else:
            # Иначе используем ручной ввод, если есть
            address_text = data.get("address_text")
            if address_text:
                cart.address_text = address_text

            # Обновляем координаты если переданы
            latitude = data.get("latitude")
            longitude = data.get("longitude")
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
      "address_id": 123,            # или ID сохраненного адреса
      "latitude": 41.3,             # для доставки
      "longitude": 69.2,
      "comment": "без васаби"       # опционально
    }
    """

    def post(self, request):
        try:
            tg_user = self._get_telegram_user(request)
            if not tg_user:
                return Response({"detail": "Invalid or unknown Telegram user"}, status=400)
            
            # Проверка времени работы
            from .utils import is_restaurant_open
            is_open, message = is_restaurant_open()
            # Для тестов/разработки можно отключить:
            # if not is_open and tg_user.username != 'admin':
            if not is_open:
                return Response({"detail": message}, status=400)

            delivery_type = request.data.get("delivery_type")
            address_text = request.data.get("address_text")
            address_id = request.data.get("address_id")
            latitude = request.data.get("latitude")
            longitude = request.data.get("longitude")
            comment = request.data.get("comment", "")
            payment_method = request.data.get("payment_method", "cash")  # По умолчанию наличные

            if delivery_type not in ("pickup", "delivery", "dine_in"):
                return Response(
                {"detail": "delivery_type must be 'pickup', 'delivery' or 'dine_in'"},
                status=400,
            )

            cart = (
                Order.objects.filter(user=tg_user, status="cart")
                .prefetch_related("items__product")
                .first()
            )
            if not cart or not cart.items.exists():
                return Response({"detail": "Cart is empty"}, status=400)

            # Логика определения адреса
            final_address_text = address_text or cart.address_text
            final_latitude = latitude if latitude is not None else cart.latitude
            final_longitude = longitude if longitude is not None else cart.longitude

            # Если передан ID адреса, он имеет приоритет
            if address_id:
                from addresses.models import UserAddress
                try:
                    user_address = UserAddress.objects.get(id=address_id, user=tg_user)
                    final_address_text = user_address.address_text
                    final_latitude = user_address.latitude
                    final_longitude = user_address.longitude
                except UserAddress.DoesNotExist:
                     pass

            # Обработка table_uuid для заказов в заведении
            table_uuid = request.data.get("table_uuid")
            if delivery_type == "dine_in":
                if not table_uuid:
                     return Response({"detail": "table_uuid required for dine_in"}, status=400)
                from qr_menu.models import QRTable
                try:
                    table = QRTable.objects.get(uuid=table_uuid)
                    cart.table = table
                except QRTable.DoesNotExist:
                     return Response({"detail": "Invalid table_uuid"}, status=400)
            
            # Валидация полей для доставки
            if delivery_type == "delivery":
                if not (final_address_text or (final_latitude is not None and final_longitude is not None)):
                    return Response(
                        {
                            "detail": "For delivery, provide address_text, address_id, or latitude+longitude"
                        },
                        status=400,
                    )

            # Заполняем заказ
            cart.delivery_type = delivery_type
            cart.address_text = final_address_text
            
            if final_latitude is not None and final_longitude is not None:
                try:
                    cart.latitude = float(final_latitude)
                    cart.longitude = float(final_longitude)
                    
                    # Рассчитываем стоимость доставки
                    if delivery_type == "delivery":
                        from .utils import calculate_delivery_cost
                        price, distance = calculate_delivery_cost(cart.latitude, cart.longitude)
                        cart.delivery_price = price
                        cart.distance_km = distance
                    else:
                        cart.delivery_price = 0
                        cart.distance_km = 0

                except (TypeError, ValueError):
                    return Response(
                        {"detail": "latitude and longitude must be numbers"}, status=400
                    )

            cart.comment = comment or cart.comment
            cart.payment_method = payment_method  # Сохраняем способ оплаты
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
            
            # Генерация ссылки на оплату (если выбрана онлайн оплата)
            # Фронтенд должен прислать payment_method='online' и payment_provider='payme' (или 'click')
            if payment_method == "online" or payment_method in ["payme", "click"]: 
                # Поддержка упрощенного варианта, если фронт шлет "payme" в payment_method
                provider = request.data.get("payment_provider")
                if not provider and payment_method in ["payme", "click"]:
                    provider = payment_method
                
                # По умолчанию payme, если provider не указан
                if not provider:
                    provider = "payme"
                
                # Используем наш процессор
                from .payment_service import PaymentProcessor
                processor = PaymentProcessor()
                
                # cart - это переменная, которая хранит оформленный заказ (статус уже 'new')
                payment_res = processor.create_payment_session(cart, provider=provider)
                
                if payment_res.get('success'):
                    response_data['payment_url'] = payment_res['payment_url']
                    response_data['payment_type'] = payment_res.get('type') # telegram_invoice or redirect
                    response_data['payment_provider'] = provider
                else:
                    # Логируем ошибку, но заказ уже создан. Можно вернуть warning.
                    print(f"Payment generation failed: {payment_res.get('error')}")
            
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            print("[CHECKOUT ERROR]", str(e))
            traceback.print_exc()
            return Response({"detail": f"Internal server error: {str(e)}"}, status=500)


class CancelOrderView(MiniAppUserMixin, APIView):
    """
    POST /api/orders/cancel_order/
    Создание запроса на отмену активного заказа (требует подтверждения оператора)
    body: { "order_id": int, "reason": str }
    """

    def post(self, request):
        from .models import OrderCancellationRequest
        
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        order_id = request.data.get("order_id")
        reason = request.data.get("reason", "")
        
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

        # Проверяем нет ли уже активного запроса
        existing_request = OrderCancellationRequest.objects.filter(
            order=order,
            status="pending"
        ).first()
        
        if existing_request:
            # Вместо ошибки возвращаем 200 с сообщением
            response_data = {
                "active_orders": [OrderSerializer(o).data for o in Order.objects.filter(user=tg_user, status__in=["new", "preparing", "delivering"]).prefetch_related("items__product").order_by("-created_at")],
                "message": "Запрос на отмену уже был отправлен и ожидает подтверждения."
            }
            return Response(response_data, status=status.HTTP_200_OK)

        # Создаем запрос на отмену
        OrderCancellationRequest.objects.create(
            order=order,
            requested_by=tg_user,
            reason=reason,
            status="pending"
        )

        # Получаем данные как обычно для обновления UI
        active_orders = (
            Order.objects.filter(user=tg_user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        response_data = {
            "active_orders": [OrderSerializer(order).data for order in active_orders],
            "message": "Запрос на отмену отправлен оператору. Ожидайте подтверждения."
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


class ValidatePromoCodeView(MiniAppUserMixin, APIView):
    """
    POST /api/orders/validate-promo/
    Проверка валидности промокода и расчет скидки
    body: { "code": str }
    """

    def post(self, request):
        from .models import PromoCode
        
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        code = request.data.get("code", "").strip().upper()
        if not code:
            return Response({"detail": "code is required"}, status=400)

        try:
            promo_code = PromoCode.objects.get(code=code)
        except PromoCode.DoesNotExist:
            return Response({"detail": "Промокод не найден"}, status=404)

        # Проверяем валидность
        is_valid, message = promo_code.is_valid()
        if not is_valid:
            return Response({"detail": message, "valid": False}, status=400)

        # Получаем текущую корзину для расчета скидки
        cart = Order.objects.filter(user=tg_user, status="cart").first()
        if not cart:
            return Response({"detail": "Корзина пуста"}, status=400)

        order_total = cart.total_price
        
        # Проверяем минимальную сумму
        if order_total < promo_code.min_order_amount:
            return Response({
                "detail": f"Минимальная сумма заказа для этого промокода: {promo_code.min_order_amount}",
                "valid": False,
                "min_order_amount": float(promo_code.min_order_amount)
            }, status=400)

        # Рассчитываем скидку
        discount = promo_code.calculate_discount(order_total)

        return Response({
            "valid": True,
            "code": promo_code.code,
            "discount_type": promo_code.discount_type,
            "discount_value": float(promo_code.discount_value),
            "discount_amount": float(discount),
            "final_price": float(order_total - discount),
            "message": "Промокод применен успешно"
        }, status=status.HTTP_200_OK)


class ApplyPromoCodeView(MiniAppUserMixin, APIView):
    """
    POST /api/orders/apply-promo/
    Применение промокода к корзине
    body: { "code": str }
    """

    def post(self, request):
        from .models import PromoCode
        from django.core.exceptions import ValidationError
        
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        code = request.data.get("code", "").strip().upper()
        if not code:
            return Response({"detail": "code is required"}, status=400)

        try:
            promo_code = PromoCode.objects.get(code=code)
        except PromoCode.DoesNotExist:
            return Response({"detail": "Промокод не найден"}, status=404)

        # Получаем корзину
        cart = Order.objects.filter(user=tg_user, status="cart").first()
        if not cart or not cart.items.exists():
            return Response({"detail": "Корзина пуста"}, status=400)

        # Применяем промокод
        try:
            cart.apply_promo_code(promo_code)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=400)

        # Обновляем корзину
        cart.refresh_from_db()
        
        # Получаем активные заказы
        active_orders = (
            Order.objects.filter(user=tg_user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        response_data = {
            "cart": OrderSerializer(cart).data,
            "active_orders": [OrderSerializer(order).data for order in active_orders],
            "message": f"Промокод {code} применен. Скидка: {cart.discount_amount}"
        }
        return Response(response_data, status=status.HTTP_200_OK)


class RequestCancelOrderItemView(MiniAppUserMixin, APIView):
    """
    POST /api/orders/request-cancel-item/
    Создание запроса на отмену товара (требует подтверждения оператора)
    body: { "order_item_id": int, "reason": str }
    """

    def post(self, request):
        from .models import OrderItemCancellationRequest
        
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        order_item_id = request.data.get("order_item_id")
        reason = request.data.get("reason", "")
        
        if not order_item_id:
            return Response({"detail": "order_item_id is required"}, status=400)

        try:
            order_item = OrderItem.objects.select_related("order").get(id=order_item_id)
        except OrderItem.DoesNotExist:
            return Response({"detail": "Order item not found"}, status=404)

        # Проверяем что заказ принадлежит пользователю
        if order_item.order.user != tg_user:
            return Response({"detail": "Unauthorized"}, status=403)

        # Проверяем что это активный заказ
        if order_item.order.status not in ("new", "preparing", "delivering"):
            return Response(
                {"detail": "Can only request cancellation for items in active orders"}, 
                status=400
            )

        # Проверяем что товар еще не отменен
        if order_item.is_canceled:
            return Response({"detail": "Item is already canceled"}, status=400)

        # Проверяем что нет активного запроса на отмену
        existing_request = OrderItemCancellationRequest.objects.filter(
            order_item=order_item,
            status="pending"
        ).first()
        
        if existing_request:
            return Response(
                {"detail": "Cancellation request already exists for this item"},
                status=400
            )

        # Создаем запрос на отмену
        cancellation_request = OrderItemCancellationRequest.objects.create(
            order_item=order_item,
            requested_by=tg_user,
            reason=reason
        )

        # Получаем обновленные данные
        cart = (
            Order.objects.filter(user=tg_user, status="cart")
            .prefetch_related("items__product")
            .first()
        )

        active_orders = (
            Order.objects.filter(user=tg_user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        response_data = {
            "cart": OrderSerializer(cart).data if cart else {"items": [], "total_price": 0},
            "active_orders": [OrderSerializer(order).data for order in active_orders],
            "message": "Запрос на отмену товара отправлен. Ожидайте подтверждения оператора."
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class ProcessCancellationRequestView(MiniAppUserMixin, APIView):
    """
    POST /api/orders/process-cancellation/
    Обработка запроса на отмену товара (только для админов/операторов)
    body: { "request_id": int, "action": "approve" | "reject" }
    """

    def post(self, request):
        from .models import OrderItemCancellationRequest
        
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response({"detail": "Invalid or unknown Telegram user"}, status=400)

        # Проверяем права администратора
        if not tg_user.is_admin:
            return Response(
                {"detail": "Access denied. Admin rights required."},
                status=403
            )

        request_id = request.data.get("request_id")
        action = request.data.get("action")
        
        if not request_id or action not in ("approve", "reject"):
            return Response(
                {"detail": "request_id and action (approve/reject) are required"},
                status=400
            )

        try:
            cancellation_request = OrderItemCancellationRequest.objects.select_related(
                "order_item__order__user"
            ).get(id=request_id)
        except OrderItemCancellationRequest.DoesNotExist:
            return Response({"detail": "Cancellation request not found"}, status=404)

        # Проверяем что запрос еще не обработан
        if cancellation_request.status != "pending":
            return Response(
                {"detail": f"Request already {cancellation_request.status}"},
                status=400
            )

        # Обрабатываем запрос
        if action == "approve":
            cancellation_request.approve(tg_user)
            message = "Запрос на отмену одобрен. Товар отменен."
        else:
            cancellation_request.reject(tg_user)
            message = "Запрос на отмену отклонен."

        # Получаем обновленные данные для пользователя, чей товар был отменен
        order_user = cancellation_request.order_item.order.user
        cart = (
            Order.objects.filter(user=order_user, status="cart")
            .prefetch_related("items__product")
            .first()
        )

        active_orders = (
            Order.objects.filter(user=order_user, status__in=["new", "preparing", "delivering"])
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        response_data = {
            "cart": OrderSerializer(cart).data if cart else {"items": [], "total_price": 0},
            "active_orders": [OrderSerializer(order).data for order in active_orders],
            "message": message
        }
        return Response(response_data, status=status.HTTP_200_OK)

class PollOrderStatusView(MiniAppUserMixin, APIView):
    """
    GET /api/orders/poll/<int:order_id>/
    Long polling endpoint для получения актуального статуса заказа
    """
    permission_classes = [AllowAny]

    def get(self, request, order_id):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response(
                {"error": "Invalid Telegram authentication"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            order = Order.objects.select_related('user', 'promo_code').prefetch_related(
                'items__product',
                'items__cancellation_requests',
                'cancellation_requests'
            ).get(id=order_id, user=tg_user)
            
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class InitiatePaymentView(MiniAppUserMixin, APIView):
    """
    POST /api/orders/initiate-payment/
    Initiates online payment for an order.
    
    Request body:
    {
        "order_id": int
    }
    
    Response:
    {
        "success": bool,
        "payment_url": str (redirect user here),
        "transaction_id": int,
        "message": str
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .payment_service import PaymentProcessor
        
        print("[InitiatePaymentView] Request received")
        print(f"[InitiatePaymentView] Headers: {dict(request.headers)}")
        print(f"[InitiatePaymentView] Body: {request.data}")
        
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            print("[InitiatePaymentView] Invalid Telegram authentication")
            return Response(
                {"success": False, "error": "Invalid Telegram authentication"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        print(f"[InitiatePaymentView] User authenticated: {tg_user}")
        
        order_id = request.data.get("order_id")
        print(f"[InitiatePaymentView] order_id: {order_id}")
        
        if not order_id:
            print("[InitiatePaymentView] order_id is missing")
            return Response(
                {"success": False, "error": "order_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = Order.objects.get(id=order_id, user=tg_user, status="new")
            print(f"[InitiatePaymentView] Order found: {order}")
        except Order.DoesNotExist:
            print(f"[InitiatePaymentView] Order not found - ID: {order_id}, User: {tg_user}, Status: new")
            return Response(
                {"success": False, "error": "Order not found or not in new status"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if order has items
        items_count = order.items.count()
        print(f"[InitiatePaymentView] Order items count: {items_count}")
        if not order.items.exists():
            print("[InitiatePaymentView] Cart is empty")
            return Response(
                {"success": False, "error": "Cart is empty"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if order has delivery info
        print(f"[InitiatePaymentView] Delivery type: {order.delivery_type}, Address: {order.address_text}")
        if not order.delivery_type or (order.delivery_type == "delivery" and not order.address_text):
            print("[InitiatePaymentView] Delivery information is incomplete")
            return Response(
                {"success": False, "error": "Delivery information is incomplete"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set payment method to online
        order.payment_method = "online"
        order.save()
        print(f"[InitiatePaymentView] Order payment_method updated to online")
        
        # Create payment session
        try:
            processor = PaymentProcessor(request=request)
            provider = request.data.get('provider') # Get provider from request
            
            print(f"[InitiatePaymentView] Creating payment session for order {order_id} with provider {provider}")
            payment_result = processor.create_payment_session(order, provider=provider)
            print(f"[InitiatePaymentView] Payment result: {payment_result}")
            
            if not payment_result.get('success'):
                print(f"[InitiatePaymentView] Payment initiation failed: {payment_result}")
                return Response(
                    payment_result,
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            print(f"[InitiatePaymentView] Payment session created successfully")
            print(f"[InitiatePaymentView] Returning response: {payment_result}")
            return Response(payment_result, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"[InitiatePaymentView] Error creating payment session: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"success": False, "error": f"Payment initiation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentCallbackView(APIView):
    """
    POST /api/orders/payment-callback/
    Webhook for handling payment callbacks from Click.
    
    For local development, also handles GET requests for mock testing.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Handle Click webhook callback via standard Click Merchant API Protocol.
        Supports Prepare (action=0) and Complete (action=1) steps.
        """
        from .click_utils import verify_click_signature, get_click_error_message
        from .models import ClickTransaction, Order
        from .tasks import process_successful_payment
        
        # Получаем данные
        data = request.data
        click_trans_id = data.get('click_trans_id')
        service_id = data.get('service_id')
        merchant_trans_id = data.get('merchant_trans_id')
        amount = data.get('amount')
        action = data.get('action')
        error = data.get('error')
        merchant_prepare_id = data.get('merchant_prepare_id')
        sign_string = data.get('sign_string')
        sign_time = data.get('sign_time')

        # Базовая структура ответа
        response_data = {
            'click_trans_id': click_trans_id,
            'merchant_trans_id': merchant_trans_id,
            'merchant_prepare_id': merchant_prepare_id,
            'error': 0,
            'error_note': 'Success'
        }

        # 1. Валидация входных данных
        try:
            action = int(action) if action is not None else -1
            amount = float(amount) if amount is not None else 0
            error = int(error) if error is not None else 0
        except ValueError:
             response_data['error'] = -8
             response_data['error_note'] = 'Invalid parameters'
             return Response(response_data)

        # 2. Проверка подписи
        # Собираем словарь параметров для проверки подписи
        sign_params = {
            'click_trans_id': click_trans_id,
            'service_id': service_id,
            'merchant_trans_id': merchant_trans_id,
            'amount': amount,
            'action': action,
            'sign_time': sign_time,
            'sign_string': sign_string,
        }
        if merchant_prepare_id:
            sign_params['merchant_prepare_id'] = merchant_prepare_id

        if not verify_click_signature(sign_params, action):
            response_data['error'] = -1
            response_data['error_note'] = 'Invalid signature'
            return Response(response_data)

        # 3. Поиск заказа
        try:
            order = Order.objects.get(id=int(merchant_trans_id))
        except (Order.DoesNotExist, ValueError):
            response_data['error'] = -5
            response_data['error_note'] = 'Order not found'
            return Response(response_data)

        # 4. Проверка суммы
        # Click присылает сумму, проверяем с точностью до 0.01
        order_amount_dec = float(order.final_price)
        if abs(amount - order_amount_dec) > 0.01:
            response_data['error'] = -2
            response_data['error_note'] = 'Incorrect parameter amount'
            return Response(response_data)


        # === ACTION 0: PREPARE (Подготовка) ===
        if action == 0:
            # Проверка статуса заказа
            if order.payment_status == 'paid':
                 response_data['error'] = -4
                 response_data['error_note'] = 'Already paid'
                 return Response(response_data)
            
            # Создаем или обновляем транзакцию
            click_transaction, _ = ClickTransaction.objects.get_or_create(
                click_trans_id=click_trans_id,
                defaults={
                    'order': order,
                    'merchant_trans_id': merchant_trans_id,
                    'amount': amount,
                    'status': 'preparing',
                    'prepare_time': timezone.now()
                }
            )
            
            # Возвращаем ID подготовки (в нашем случае ID транзакции)
            response_data['merchant_prepare_id'] = click_transaction.id
            return Response(response_data)


        # === ACTION 1: COMPLETE (Завершение) ===
        elif action == 1:
            try:
                # Ищем транзакцию по merchant_prepare_id (который мы вернули на шаге 0)
                click_transaction = ClickTransaction.objects.get(id=int(merchant_prepare_id))
            except (ClickTransaction.DoesNotExist, ValueError, TypeError):
                 response_data['error'] = -6
                 response_data['error_note'] = 'Transaction not found'
                 return Response(response_data)
            
            # Если от Click пришла ошибка (отмена оплаты)
            if error < 0:
                click_transaction.status = 'error'
                click_transaction.error_code = error
                click_transaction.error_note = 'Cancelled by Click'
                click_transaction.save()
                return Response(response_data) # Возвращаем успех, но транзакция помечена как ошибка

            # Если заказ уже оплачен
            if click_transaction.status == 'confirmed':
                 response_data['error'] = -4
                 response_data['error_note'] = 'Already paid'
                 return Response(response_data)

            # УСПЕХ!
            click_transaction.status = 'confirmed'
            click_transaction.complete_time = timezone.now()
            click_transaction.save()

            order.payment_status = 'paid'
            order.transaction_id = str(click_transaction.click_trans_id)
            order.paid_at = timezone.now()
            # Можно также перевести статус заказа в "new" или "preparing"
            if order.status == 'cart':
                 order.status = 'new'
            order.save()
            
            # Запускаем Celery задачу
            process_successful_payment.delay(order.id, amount)

            return Response(response_data)

        
        # Неизвестное действие
        response_data['error'] = -3
        response_data['error_note'] = 'Action not found'
        return Response(response_data)
    
    def get(self, request):
        """Mock payment callback for local testing."""
        from .payment_service import PaymentProcessor
        
        order_id = request.GET.get('order_id')
        amount = request.GET.get('amount')
        
        if not order_id or not amount:
            return Response(
                {"error": "order_id and amount are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Simulate successful payment
        processor = PaymentProcessor()
        result = processor.handle_payment_callback(
            click_trans_id=999999,
            merchant_trans_id=order_id,
            amount=Decimal(str(amount)),
            status='completed'
        )
        
        if result.get('success'):
            # Update order status
            try:
                order = Order.objects.get(id=int(order_id))
                order.status = 'new'
                order.save()
            except Order.DoesNotExist:
                pass
            
            return Response(
                {
                    "success": True,
                    "message": "[MOCK] Payment simulated successfully",
                    "order_id": int(order_id),
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"success": False, "error": result.get('error')},
                status=status.HTTP_400_BAD_REQUEST
            )


class CheckPaymentStatusView(MiniAppUserMixin, APIView):
    """
    GET /api/orders/payment-status/<int:order_id>/
    Check payment status for an order.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, order_id):
        tg_user = self._get_telegram_user(request)
        if not tg_user:
            return Response(
                {"error": "Invalid Telegram authentication"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            order = Order.objects.get(id=order_id, user=tg_user)
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get latest Click transaction if exists
        click_transaction = order.click_transactions.first() if hasattr(order, 'click_transactions') else None
        
        return Response(
            {
                "order_id": order.id,
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,
                "paid_at": order.paid_at,
                "amount": str(order.final_price),
                "transaction": {
                    "id": click_transaction.id if click_transaction else None,
                    "status": click_transaction.status if click_transaction else None,
                    "click_trans_id": click_transaction.click_trans_id if click_transaction else None,
                } if click_transaction else None,
            },
            status=status.HTTP_200_OK
        )


class MockPaymentCallbackView(APIView):
    """
    GET /api/orders/payment/mock-callback/
    Mock payment callback for local development.
    Simulates Click payment webhook response.
    
    Query params:
    - order_id: int (required)
    - amount: Decimal (required)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Handle mock payment callback (for local development)."""
        from .payment_service import PaymentProcessor
        from .models import ClickTransaction
        
        print("[MockPaymentCallbackView] Mock payment callback received")
        
        order_id = request.query_params.get('order_id')
        amount = request.query_params.get('amount')
        
        print(f"[MockPaymentCallbackView] order_id: {order_id}, amount: {amount}")
        
        if not order_id or not amount:
            print("[MockPaymentCallbackView] Missing order_id or amount")
            return Response(
                {"error": "Missing order_id or amount"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = Order.objects.get(id=int(order_id))
            print(f"[MockPaymentCallbackView] Order found: {order.id}")
        except Order.DoesNotExist:
            print(f"[MockPaymentCallbackView] Order not found: {order_id}")
            return Response(
                {"error": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update order status
        order.status = 'new'  # Keep as new status
        order.payment_status = 'paid'
        order.paid_at = timezone.now()
        order.save()
        print(f"[MockPaymentCallbackView] Order updated - status: paid")
        
        # Create or update ClickTransaction
        transaction = ClickTransaction.objects.create(
            order=order,
            click_trans_id=999999,  # Mock transaction ID
            merchant_trans_id=str(order_id),
            amount=Decimal(str(amount)),
            status='confirmed',
            complete_time=timezone.now()
        )
        print(f"[MockPaymentCallbackView] Transaction created: {transaction.id}")
        
        return Response(
            {
                "success": True,
                "message": "Mock payment processed successfully",
                "order_id": int(order_id),
                "status": "paid"
            },
            status=status.HTTP_200_OK
        )

class OrderReceiptView(APIView):
    """
    GET /api/orders/<int:order_id>/receipt/
    Generates an HTML receipt for the order.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, order_id):
        from .models import Order
        from django.shortcuts import render
        from django.http import HttpResponse
        
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return HttpResponse("Заказ не найден", status=404)
        
        # Разрешаем просмотр, если это публичный чек
        # В идеале нужно проверять владельца, но для ссылки из бота это допустимо
        
        context = {
            "order": order,
            "items": order.items.select_related('product').all(),
            "date": order.created_at,
            "total": order.final_price,
            "payment_method": order.get_payment_method_display(),
            "payment_status": order.get_payment_status_display(),
            "is_paid": order.payment_status == 'paid',
        }
        
        # Simple HTML template inline for simplicity, or use a file
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Чек заказа #{order.id}</title>
            <style>
                body {{ font-family: 'Courier New', Courier, monospace; background: #f5f5f5; padding: 20px; }}
                .receipt {{ max-width: 400px; margin: 0 auto; background: white; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-radius: 5px; }}
                .header {{ text-align: center; margin-bottom: 20px; border-bottom: 2px dashed #ccc; padding-bottom: 15px; }}
                .logo {{ font-size: 24px; font-weight: bold; margin-bottom: 5px; }}
                .info {{ font-size: 14px; color: #555; margin-bottom: 5px; }}
                .items {{ margin-bottom: 20px; width: 100%; border-collapse: collapse; }}
                .items th {{ text-align: left; border-bottom: 1px solid #eee; padding: 5px 0; font-size: 12px; }}
                .items td {{ padding: 5px 0; font-size: 14px; border-bottom: 1px dashed #eee; }}
                .total {{ margin-top: 20px; border-top: 2px dashed #000; padding-top: 10px; font-weight: bold; font-size: 18px; display: flex; justify-content: space-between; }}
                .footer {{ margin-top: 30px; text-align: center; font-size: 12px; color: #888; }}
                .status-paid {{ color: green; border: 2px solid green; display: inline-block; padding: 5px 10px; transform: rotate(-10deg); margin-top: 10px; font-size: 20px; opacity: 0.8; }}
                .status-unpaid {{ color: red; border: 2px solid red; display: inline-block; padding: 5px 10px; font-size: 20px; opacity: 0.8; }}
            </style>
        </head>
        <body>
            <div class="receipt">
                <div class="header">
                    <div class="logo">KY SUSHI</div>
                    <div class="info">Джизак, ул. Орзу Махмудов, 11</div>
                    <div class="info">+998 (90) 123-45-67</div>
                    <div class="info">Заказ #{order.id}</div>
                    <div class="info">{order.created_at.strftime('%d.%m.%Y %H:%M')}</div>
                    
                    {'<div class="status-paid">ОПЛАЧЕНО</div>' if order.payment_status == 'paid' else '<div class="status-unpaid">НЕ ОПЛАЧЕНО</div>'}
                </div>
                
                <table class="items">
                    <thead>
                        <tr>
                            <th>Товар</th>
                            <th style="text-align: right;">Сумма</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for item in context['items']:
            item_total = item.price * item.quantity
            html_content += f"""
                        <tr>
                            <td>
                                {item.product.name}<br>
                                <span style="font-size: 11px; color: #888;">{item.quantity} x {item.price:,.0f}</span>
                            </td>
                            <td style="text-align: right;">{item_total:,.0f}</td>
                        </tr>
            """
            
        html_content += f"""
                    </tbody>
                </table>
                
                <div class="total">
                    <span>ИТОГО:</span>
                    <span>{order.final_price:,.0f} сум</span>
                </div>
                
                <div style="margin-top: 10px; font-size: 13px;">
                    <div>Способ оплаты: {order.get_payment_method_display()}</div>
                    <div>Доставка: {order.get_delivery_type_display()}</div>
                </div>
                
                <div class="footer">
                    Спасибо за заказ!<br>
                    Приятного аппетита 🍣
                </div>
            </div>
            
            <script>
                // Автоматически предложить печать, если открыто на десктопе
                if (!(/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent))) {{
                   // window.print(); // Можно раскомментировать
                }}
            </script>
        </body>
        </html>
        """
        
        return HttpResponse(html_content)

class CalculateDeliveryView(APIView):
    """
    Рассчитывает стоимость доставки по координатам
    POST /api/orders/calculate-delivery/
    body: { latitude: float, longitude: float }
    """
    permission_classes = [AllowAny] 
    
    def post(self, request):
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        
        if lat is None or lng is None:
            # Если координат нет, можно вернуть какую-то дефолтную (базовую) цену
            # Но лучше ошибку, чтобы фронт знал
            from .models import RestaurantSettings
            s, _ = RestaurantSettings.objects.get_or_create(pk=1)
            return Response({
                'price': s.delivery_base_price,
                'distance_km': 0,
                'formatted_price': f"{int(s.delivery_base_price):,} сум".replace(",", " ")
            })
            
        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
             return Response({'error': 'Invalid coordinates'}, status=400)
            
        from .utils import calculate_delivery_cost
        price, distance = calculate_delivery_cost(lat, lng)
        
        return Response({
            'price': price,
            'distance_km': distance,
            'formatted_price': f"{int(price):,} сум".replace(",", " ")
        })
