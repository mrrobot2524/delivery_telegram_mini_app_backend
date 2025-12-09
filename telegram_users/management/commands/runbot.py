from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    MenuButtonWebApp,
    LabeledPrice, # Для инвойсов
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler, # Импорт обработчика предоплаты
    ContextTypes,
    filters,
)

from telegram_users.models import TelegramUser
from menu.models import Category, Product
from orders.models import Order, OrderItem


WEBAPP_URL = "https://tss7pc8k-5173.euw.devtunnels.ms/"  # TODO: заменить на боевой URL


class Command(BaseCommand):
    help = "Run Telegram bot"

    # ========= service helpers =========

    async def get_or_create_telegram_user(self, user):
        tg_user, _ = await sync_to_async(TelegramUser.objects.get_or_create)(
            telegram_id=user.id,
            defaults={
                "username": user.username,
                "first_name": user.first_name,
            },
        )
        return tg_user

    async def get_or_create_cart(self, tg_user):
        cart, _ = await sync_to_async(Order.objects.get_or_create)(
            user=tg_user,
            status="cart",
            defaults={},
        )
        return cart

    async def add_product_to_cart(self, tg_user, product):
        cart = await self.get_or_create_cart(tg_user)
        item, created = await sync_to_async(OrderItem.objects.get_or_create)(
            order=cart,
            product=product,
            defaults={"quantity": 1, "price": product.price},
        )
        if not created:
            item.quantity += 1
            await sync_to_async(item.save)()
        return cart

    # ============== handle() ==============

    def handle(self, *args, **options):
        application = ApplicationBuilder().token(
            settings.TELEGRAM_BOT_TOKEN
        ).build()

        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.CONTACT, self.save_contact))

        # Обработчик кнопки "Начать" - делает то же самое, что и /start
        application.add_handler(
            MessageHandler(filters.TEXT & filters.Regex(r"^🚀 Начать$"), self.start)
        )

        # Обработчики оплаты (Payme / Telegram Payments)
        application.add_handler(PreCheckoutQueryHandler(self.precheckout_callback))
        application.add_handler(
            MessageHandler(filters.SUCCESSFUL_PAYMENT, self.successful_payment_callback)
        )

        application.run_polling()

        # Старые обработчики отключены
        # application.add_handler(CommandHandler("menu", self.menu))
        # application.add_handler(
        #    MessageHandler(filters.TEXT & filters.Regex(r"^🍣 Меню$"), self.menu)
        # )


    # ============== /start ==============

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        tg_user = await self.get_or_create_telegram_user(user)

        # если телефона нет — просим контакт
        if not tg_user.phone_number:
            contact_button = KeyboardButton(
                text="Отправить телефон",
                request_contact=True,
            )
            keyboard = ReplyKeyboardMarkup(
                [[contact_button]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
            if update.message:
                await update.message.reply_text(
                    "Привет! Нажми кнопку, чтобы поделиться номером телефона.",
                    reply_markup=keyboard,
                )
            return
            
        # Устанавливаем кнопку "Menu" (слева от поля ввода)
        try:
            await context.bot.set_chat_menu_button(
                chat_id=update.effective_chat.id,
                menu_button=MenuButtonWebApp(text="Заказать 🍣", web_app=WebAppInfo(url=WEBAPP_URL))
            )
        except Exception as e:
            print(f"Error setting menu button: {e}")

        # если уже зарегистрирован — показываем меню и кнопку Mini App
        await self._send_main_menu_with_webapp(update)

    # вынесено в отдельный метод: главное меню + кнопка Mini App
    async def _send_main_menu_with_webapp(self, update: Update):
        main_keyboard = ReplyKeyboardMarkup(
            [
                # Кнопка перезапуска (отправляет /start по сути)
                [KeyboardButton(text="🚀 Начать")],
            ],
            resize_keyboard=True,
        )

        if update.message:
            # Отправляем инлайн кнопку
            inline_kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="📱 Открыть приложение",
                            web_app=WebAppInfo(url=WEBAPP_URL),
                        )
                    ]
                ]
            )
            
            await update.message.reply_text(
                "Добро пожаловать в KY Sushi! 🍣\nДля заказа нажмите кнопку ниже:",
                reply_markup=inline_kb,
            )
            
            # И дублируем Reply кнопку
            await update.message.reply_text(
                " 👇",
                reply_markup=main_keyboard,
            )

    # ============== save_contact ==============

    async def save_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        contact = update.message.contact if update.message else None

        photo_file_id = None
        photo_rel_path = None

        # пробуем получить аватар
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo_file_id = photos.photos[0][0].file_id

            telegram_file = await context.bot.get_file(photo_file_id)

            filename = f"telegram_avatars/{user.id}.jpg"
            full_path = settings.MEDIA_ROOT / filename
            full_path.parent.mkdir(parents=True, exist_ok=True)

            await telegram_file.download_to_drive(str(full_path))
            photo_rel_path = filename

        if contact:
            await sync_to_async(TelegramUser.objects.update_or_create)(
                telegram_id=user.id,
                defaults={
                    "username": user.username,
                    "first_name": user.first_name,
                    "phone_number": contact.phone_number,
                    "photo_file_id": photo_file_id,
                    "photo": photo_rel_path,
                },
            )

        # после регистрации сразу показываем меню + Mini App
        await self._send_main_menu_with_webapp(update)

    # ============== PAYMENTS (PAYME) ==============

    async def precheckout_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ответ на запрос пре-чекаута (проверка перед оплатой)."""
        query = update.pre_checkout_query
        # Если нужно, здесь можно проверить наличие товара на складе.
        # Пока просто одобряем.
        if query.invoice_payload != "custom-payload":
             # В payload мы будем класть order_id. Сейчас простой пример.
             # Хотя лучше сразу проверять order_id
             pass
        
        # Одобряем платеж
        await query.answer(ok=True)

    async def successful_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка успешного платежа."""
        message = update.message
        successful_payment = message.successful_payment
        
        # Получаем order_id из payload
        payload = successful_payment.invoice_payload
        
        # Пытаемся найти и обновить заказ
        try:
            order_id = int(payload)
            # Обновляем статус заказа в БД асинхронно
            order = await sync_to_async(Order.objects.get)(id=order_id)
            
            # Меняем статус на paid
            order.payment_status = "paid"
            order.payment_method = "online" # Payme
            order.transaction_id = successful_payment.provider_payment_charge_id
            # Если статус был new, можно оставить new или поменять
            order.paid_at = timezone.now()
            await sync_to_async(order.save)()
            
            # Отправляем подтверждение пользователю
            # Формируем ссылку на чек
            # Хак для devtunnels: меняем порт 5173 на 8000
            api_base = WEBAPP_URL.replace("-5173", "-8000").rstrip('/')
            receipt_url = f"{api_base}/api/orders/{order_id}/receipt/"

            await update.message.reply_text(
                f"✅ Оплата прошла успешно! Ваш заказ #{order_id} принят в работу. Спасибо!\n\n"
                f"📄 Ваш чек: {receipt_url}"
            )
            
            # TODO: Можно отправить уведомление админу или на кухню
            
        except (ValueError, Order.DoesNotExist):
            await update.message.reply_text(
                "✅ Оплата прошла, но мы не смогли найти номер заказа. Свяжитесь с поддержкой."
            )
        except Exception as e:
            print(f"Payment Error: {e}")

    # Старые методы menu, cart и т.д. можно удалить, они больше не используются
