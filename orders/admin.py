from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, PromoCode, Promotion, OrderItemCancellationRequest, OrderCancellationRequest


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("total_price", "is_canceled", "canceled_at")
    fields = ("product", "quantity", "price", "total_price", "is_canceled", "canceled_at")
    raw_id_fields = ("product",)
    
    def product_image(self, obj):
        if obj.product and obj.product.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.product.image.url
            )
        return "—"
    product_image.short_description = "Фото"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_link",
        "status_badge",
        "status",
        "delivery_type",
        "payment_method_badge",
        "payment_status_badge",
        "estimated_time",
        "address_short",
        "total_price_format",
        "created_at",
    )
    list_filter = ("status", "delivery_type", "created_at")
    search_fields = ("id", "user__username", "user__first_name", "user__phone_number", "address_text")
    readonly_fields = ("created_at", "updated_at", "total_price_display", "final_price_display", "map_view")
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    list_per_page = 20
    list_editable = ("status", "estimated_time")
    raw_id_fields = ("user", "promo_code")
    
    fieldsets = (
        ("Клиент и Статус", {
            "fields": (
                ("user", "user_link_readonly"), 
                "status", 
                "estimated_time",
                "created_at"
            )
        }),
        ("📍 Доставка и Адрес", {
            "fields": (
                "delivery_type", 
                "address_text", 
                ("latitude", "longitude"),
                "map_view"
            ),
            "classes": ("extrapretty",),
        }),
        ("💰 Оплата и Скидки", {
            "fields": (
                ("payment_method", "payment_status", "paid_at"),
                "promo_code", 
                ("total_price_display", "discount_amount", "final_price_display"),
                "comment"
            )
        }),
        ("Системная информация", {
            "fields": ("updated_at",),
            "classes": ("collapse",),
        }),
    )
    
    class Media:
        css = {
            'all': (
                'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
                'https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css',
            )
        }
        js = (
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
            'https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js',
        )


    actions = ["make_preparing", "make_delivering", "make_done", "make_canceled", "mark_as_paid", "generate_receipt"]


    @admin.action(description="Перевести в статус 'Готовится'")
    def make_preparing(self, request, queryset):
        updated = queryset.update(status="preparing")
        self.message_user(request, f"{updated} заказов переведено в статус 'Готовится'.")

    @admin.action(description="Перевести в статус 'Доставляется'")
    def make_delivering(self, request, queryset):
        updated = queryset.update(status="delivering")
        self.message_user(request, f"{updated} заказов переведено в статус 'Доставляется'.")
    
    @admin.action(description="Перевести в статус 'Завершён'")
    def make_done(self, request, queryset):
        updated = queryset.update(status="done")
        self.message_user(request, f"{updated} заказов переведено в статус 'Завершён'.")

    @admin.action(description="Перевести в статус 'Отменён'")
    def make_canceled(self, request, queryset):
        updated = queryset.update(status="canceled")
        self.message_user(request, f"{updated} заказов отменено.")
    
    @admin.action(description="✅ Отметить как оплаченный")
    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(payment_status="paid", paid_at=timezone.now())
        self.message_user(request, f"{updated} заказов отмечено как оплаченные.", level='success')
    
    @admin.action(description="🧾 Сгенерировать чек")
    def generate_receipt(self, request, queryset):
        from django.http import HttpResponse
        
        if queryset.count() != 1:
            self.message_user(request, "Выберите только один заказ для генерации чека.", level='error')
            return
        
        order = queryset.first()
        
        # Строим список товаров
        items_html = ""
        for item in order.items.all():
            items_html += f'<div class="item"><span>{item.product.name} x{item.quantity}</span><span>{item.total_price} сум</span></div>'
        
        # Добавляем скидку если она есть
        discount_html = ""
        if order.discount_amount > 0:
            discount_html = f'<div class="item"><span>Скидка:</span><span>-{order.discount_amount} сум</span></div>'
        
        # Добавляем адрес если он есть
        address_html = ""
        if order.address_text:
            address_html = f'<p>{order.address_text}</p>'
        
        # Генерируем HTML чек
        receipt_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Чек #{order.id}</title>
    <style>
        body {{ font-family: 'Courier New', monospace; max-width: 300px; margin: 20px auto; }}
        .header {{ text-align: center; border-bottom: 2px dashed #000; padding-bottom: 10px; margin-bottom: 10px; }}
        .item {{ display: flex; justify-content: space-between; margin: 5px 0; }}
        .total {{ border-top: 2px dashed #000; padding-top: 10px; margin-top: 10px; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>KY SUSHI</h2>
        <p>Чек #{order.id}</p>
        <p>{order.created_at.strftime('%d.%m.%Y %H:%M')}</p>
    </div>
    
    <div class="items">
        {items_html}
    </div>
    
    <div class="total">
        <div class="item"><span>Итого:</span><span>{order.total_price} сум</span></div>
        {discount_html}
        <div class="item"><span>К оплате:</span><span>{order.final_price} сум</span></div>
    </div>
    
    <div class="footer">
        <p>Способ оплаты: {order.get_payment_method_display()}</p>
        <p>Статус: {order.get_payment_status_display()}</p>
        <p>Доставка: {order.get_delivery_type_display()}</p>
        {address_html}
        <p>Спасибо за заказ!</p>
    </div>
</body>
</html>"""
        
        response = HttpResponse(receipt_html, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = f'inline; filename="receipt_{order.id}.html"'
        return response


    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'promo_code').prefetch_related('items__product')

    def user_link(self, obj):
        if obj.user:
            url = f"/admin/telegram_users/telegramuser/{obj.user.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.user)
        return "-"
    user_link.short_description = 'Клиент'
    user_link.admin_order_field = 'user__first_name'

    def user_link_readonly(self, obj):
        return self.user_link(obj)
    user_link_readonly.short_description = "Профиль клиента"

    def address_short(self, obj):
        if not obj.address_text:
            return "-"
        return (obj.address_text[:30] + '...') if len(obj.address_text) > 30 else obj.address_text
    address_short.short_description = "Адрес"

    def status_badge(self, obj):
        colors = {
            'cart': '#6c757d',      # gray
            'new': '#007bff',       # blue
            'preparing': '#fd7e14', # orange
            'delivering': '#6f42c1',# purple
            'done': '#28a745',      # green
            'canceled': '#dc3545',  # red
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Статус (бейдж)"
    
    def payment_method_badge(self, obj):
        icons = {
            'cash': '💵',
            'card': '💳',
        }
        colors = {
            'cash': '#28a745',  # green
            'card': '#007bff',  # blue
        }
        icon = icons.get(obj.payment_method, '💰')
        color = colors.get(obj.payment_method, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_payment_method_display()
        )
    payment_method_badge.short_description = "Способ оплаты"
    
    def payment_status_badge(self, obj):
        colors = {
            'pending': '#ffc107',  # yellow/warning
            'paid': '#28a745',     # green/success
        }
        icons = {
            'pending': '⏳',
            'paid': '✅',
        }
        color = colors.get(obj.payment_status, '#6c757d')
        icon = icons.get(obj.payment_status, '❓')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = "Статус оплаты"
    status_badge.admin_order_field = 'status'
    
    def total_price_format(self, obj):
        return f"{int(obj.total_price):,} сум".replace(",", " ")
    total_price_format.short_description = 'Сумма'
    total_price_format.admin_order_field = 'total_price'
    
    def total_price_display(self, obj):
        return f"{int(obj.total_price):,} сум".replace(",", " ")
    total_price_display.short_description = "Сумма товаров"
    
    def final_price_display(self, obj):
        return f"{int(obj.final_price):,} сум".replace(",", " ")
    final_price_display.short_description = "Итого к оплате"
    
    def map_view(self, obj):
        if not obj.latitude or not obj.longitude:
            return format_html('<div style="color: #666; padding: 10px; background: #f8f9fa; border: 1px solid #ddd;">Координаты не указаны</div>')
            
        # Координаты ресторана (Точка А)
        rest_lat = 40.1288875
        rest_lng = 67.8244219
        
        # Координаты клиента (Точка Б)
        lat = str(obj.latitude).replace(',', '.')
        lng = str(obj.longitude).replace(',', '.')
        
        yandex_url = f"https://yandex.ru/maps/?pt={lng},{lat}&z=17&l=map"
        google_url = f"https://www.google.com/maps?q={lat},{lng}"
        
        return format_html(
            '''
            <div style="margin-bottom: 10px;">
                <a href="{yandex}" target="_blank" style="margin-right: 10px; padding: 5px 10px; background: #fc3f1d; color: white; text-decoration: none; border-radius: 4px;">Open in Yandex Maps</a>
                <a href="{google}" target="_blank" style="margin-right: 10px; padding: 5px 10px; background: #4285F4; color: white; text-decoration: none; border-radius: 4px;">Open in Google Maps</a>
                <button type="button" onclick="navigator.clipboard.writeText('{lat}, {lng}'); this.innerText = 'Copied!';" style="padding: 5px 10px; cursor: pointer; background: #eee; border: 1px solid #ccc; border-radius: 4px; transition: all 0.2s;">Copy Coordinates</button>
                <button type="button" onclick="copyCourierInfo('{phone}', '{address}', '{lat}', '{lng}', '{yandex}', '{google}'); alert('Информация для курьера скопирована!');" style="margin-left: 10px; padding: 5px 10px; cursor: pointer; background: #28a745; color: white; border: none; border-radius: 4px;">Copy for Courier 📋</button>
            </div>
            <script>
                function copyCourierInfo(phone, address, lat, lng, yandex, google) {{
                    const text = `📦 Новый заказ!\\n\\n📍 Адрес: ${{address}}\\n📞 Телефон: ${{phone}}\\n\\n🗺 Карты:\\nGoogle: ${{google}}\\nYandex: ${{yandex}}\\n\\nКоординаты: ${{lat}}, ${{lng}}`;
                    navigator.clipboard.writeText(text);
                }}
            </script>
            <style>
                .leaflet-routing-container {{ display: none !important; }}
            </style>
            <div id="admin-map-{id}" style="height: 350px; width: 100%; max-width: 650px; border-radius: 8px; border: 1px solid #ccc;"></div>
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    if (typeof L !== 'undefined' && typeof L.Routing !== 'undefined') {{
                        var map = L.map('admin-map-{id}');
                        
                        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                            attribution: '© OpenStreetMap contributors'
                        }}).addTo(map);
                        
                        // Icon for Restaurant (Red)
                        var containerIcon = L.icon({{
                            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                            popupAnchor: [1, -34],
                            shadowSize: [41, 41]
                        }});
                        
                        // Icon for Client (Blue)
                        var clientIcon = L.icon({{
                            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
                            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                            popupAnchor: [1, -34],
                            shadowSize: [41, 41]
                        }});

                        var restLat = {rest_lat};
                        var restLng = {rest_lng};
                        var clientLat = {lat};
                        var clientLng = {lng};

                        // Маркер ресторана
                        L.marker([restLat, restLng], {{icon: containerIcon}}).addTo(map)
                            .bindPopup('<b>Точка А: Ресторан (KY Sushi)</b><br>Отсюда забираем');

                        // Маркер клиента
                        L.marker([clientLat, clientLng], {{icon: clientIcon}}).addTo(map)
                            .bindPopup('<b>Точка Б: Клиент</b><br>{address}')
                            .openPopup();
                            
                        // Прокладка реального маршрута (Routing Machine)
                        var control = L.Routing.control({{
                            waypoints: [
                                L.latLng(restLat, restLng),
                                L.latLng(clientLat, clientLng)
                            ],
                            routeWhileDragging: false,
                            addWaypoints: false,
                            draggableWaypoints: false,
                            lineOptions: {{
                                styles: [{{color: '#6610f2', opacity: 0.7, weight: 5}}]
                            }},
                            createMarker: function() {{ return null; }}, // Не создавать дефолтные маркеры
                            show: false // Скрыть текстовое описание
                        }}).addTo(map);
                        
                        // Зумим карту по маршруту, когда он найден
                        control.on('routesfound', function(e) {{
                            var routes = e.routes;
                            // map.fitBounds(routes[0].coordinates); // Routing Machine делает это сам по умолчанию (fitSelectedRoutes: true)
                        }});
                    }}
                }});
            </script>
            ''',
            id=obj.id,
            lat=lat,
            lng=lng,
            rest_lat=rest_lat,
            rest_lng=rest_lng,
            yandex=yandex_url,
            google=google_url,
            address=obj.address_text or "Точка доставки",
            phone=obj.user.phone_number if obj.user else "-"
        )
    map_view.short_description = "Маршрут (Road)"
    map_view.allow_tags = True
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ("user_link_readonly",)
        return self.readonly_fields


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order_link", "product", "quantity", "price", "total_price", "is_canceled")
    list_filter = ("is_canceled", "order__status")
    search_fields = ("product__name", "order__id")
    readonly_fields = ("total_price", "canceled_at")
    raw_id_fields = ("product", "order")
    
    def order_link(self, obj):
        if obj.order:
            url = f"/admin/orders/order/{obj.order.id}/change/"
            return format_html('<a href="{}">Заказ #{}</a>', url, obj.order.id)
        return "-"
    order_link.short_description = 'Заказ'
    order_link.admin_order_field = 'order__id'


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "discount_value",
        "min_order_amount",
        "current_uses",
        "max_uses",
        "is_active",
        "valid_from",
        "valid_until",
    )
    list_filter = ("discount_type", "is_active", "valid_from", "valid_until")
    search_fields = ("code",)
    readonly_fields = ("current_uses", "created_at")
    
    fieldsets = (
        ("Основная информация", {
            "fields": ("code", "is_active")
        }),
        ("Скидка", {
            "fields": ("discount_type", "discount_value", "min_order_amount")
        }),
        ("Ограничения", {
            "fields": ("max_uses", "current_uses", "valid_from", "valid_until")
        }),
        ("Системная информация", {
            "fields": ("created_at",)
        }),
    )


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "discount_type",
        "discount_value",
        "is_active",
        "valid_from",
        "valid_until",
    )
    list_filter = ("discount_type", "is_active", "valid_from", "valid_until")
    search_fields = ("name", "description")
    filter_horizontal = ("products",)
    readonly_fields = ("created_at",)
    
    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "description", "is_active")
        }),
        ("Скидка", {
            "fields": ("discount_type", "discount_value")
        }),
        ("Товары", {
            "fields": ("products",)
        }),
        ("Период действия", {
            "fields": ("valid_from", "valid_until")
        }),
        ("Системная информация", {
            "fields": ("created_at",)
        }),
    )


@admin.register(OrderItemCancellationRequest)
class OrderItemCancellationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order_item",
        "requested_by",
        "status",
        "requested_at",
        "processed_by",
        "processed_at",
    )
    list_filter = ("status", "requested_at", "processed_at")
    search_fields = (
        "order_item__product__name",
        "requested_by__username",
        "requested_by__first_name",
    )
    readonly_fields = ("requested_at", "processed_at")
    
    fieldsets = (
        ("Запрос", {
            "fields": ("order_item", "requested_by", "reason", "requested_at")
        }),
        ("Обработка", {
            "fields": ("status", "processed_by", "processed_at")
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Делаем некоторые поля readonly после создания"""
        if obj:  # Редактирование существующего объекта
            return self.readonly_fields + ("order_item", "requested_by", "reason")
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        """Обработка изменения статуса"""
        if change and "status" in form.changed_data:
            # Получаем оператора (пользователя админки)
            # В реальном проекте нужно связать Django User с TelegramUser
            # Для простоты пока берем первого админа из TelegramUser
            from telegram_users.models import TelegramUser
            operator = TelegramUser.objects.filter(is_admin=True).first()
            
            if obj.status == "approved":
                obj.approve(operator)
            elif obj.status == "rejected":
                obj.reject(operator)
        else:
            super().save_model(request, obj, form, change)


@admin.register(OrderCancellationRequest)
class OrderCancellationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "requested_by",
        "status",
        "requested_at",
        "processed_by",
        "processed_at",
    )
    list_filter = ("status", "requested_at", "processed_at")
    search_fields = (
        "order__id",
        "requested_by__username",
        "requested_by__first_name",
    )
    readonly_fields = ("requested_at", "processed_at")
    
    fieldsets = (
        ("Запрос", {
            "fields": ("order", "requested_by", "reason", "requested_at")
        }),
        ("Обработка", {
            "fields": ("status", "processed_by", "processed_at")
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Делаем некоторые поля readonly после создания"""
        if obj:  # Редактирование существующего объекта
            return self.readonly_fields + ("order", "requested_by", "reason")
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        """Обработка изменения статуса"""
        if change and "status" in form.changed_data:
            from telegram_users.models import TelegramUser
            operator = TelegramUser.objects.filter(is_admin=True).first()
            
            if obj.status == "approved":
                obj.approve(operator)
            elif obj.status == "rejected":
                obj.reject(operator)
        else:
            super().save_model(request, obj, form, change)
        return self.readonly_fields
