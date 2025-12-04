from django.core.management.base import BaseCommand
from django.conf import settings

from asgiref.sync import sync_to_async

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
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

        application.add_handler(CommandHandler("menu", self.menu))
        application.add_handler(
            MessageHandler(filters.TEXT & filters.Regex(r"^🍣 Меню$"), self.menu)
        )

        application.add_handler(
            MessageHandler(filters.TEXT & filters.Regex(r"^🧺 Корзина$"), self.cart)
        )

        # выбор категорий/товаров по тексту
        application.add_handler(
            MessageHandler(filters.TEXT, self.category_or_product_by_text)
        )

        application.run_polling()

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

        # если уже зарегистрирован — показываем меню и кнопку Mini App
        await self._send_main_menu_with_webapp(update)

    # вынесено в отдельный метод: главное меню + кнопка Mini App
    async def _send_main_menu_with_webapp(self, update: Update):
        main_keyboard = ReplyKeyboardMarkup(
            [
                [KeyboardButton(text="🍣 Меню")],
                [KeyboardButton(text="🧺 Корзина")],
            ],
            resize_keyboard=True,
        )

        if update.message:
            # обычное меню
            await update.message.reply_text(
                "Снова привет! Выбирай действие 👇",
                reply_markup=main_keyboard,
            )

            # inline‑кнопка для открытия Mini App
            inline_kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Открыть мини‑приложение",
                            web_app=WebAppInfo(url=WEBAPP_URL),
                        )
                    ]
                ]
            )
            await update.message.reply_text(
                "Можешь пользоваться мини‑приложением 👇",
                reply_markup=inline_kb,
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

    # ============== /menu ==============

    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user

        is_registered = await sync_to_async(
            TelegramUser.objects.filter(
                telegram_id=user.id,
                phone_number__isnull=False,
            ).exists
        )()
        if not is_registered:
            if update.message:
                await update.message.reply_text("Сначала зарегистрируйся через /start 📲")
            return

        categories = await sync_to_async(list)(
            Category.objects.filter(is_active=True)
        )
        if not categories:
            if update.message:
                await update.message.reply_text("Пока нет доступных категорий.")
            return

        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(text=cat.name)] for cat in categories],
            resize_keyboard=True,
        )

        if update.message:
            await update.message.reply_text(
                "Выбери категорию:",
                reply_markup=keyboard,
            )

    # ============== категории / товары по тексту ==============

    async def category_or_product_by_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        if not update.message:
            return

        text = (update.message.text or "").strip()
        if not text or text.startswith("/"):
            return

        user = update.effective_user

        # 1. пробуем как категорию
        category = await sync_to_async(
            Category.objects.filter(name=text, is_active=True).first
        )()
        if category:
            products = await sync_to_async(list)(
                Product.objects.filter(category=category, is_active=True)
            )
            if not products:
                await update.message.reply_text(
                    f"В категории «{category.name}» пока нет товаров."
                )
                return

            keyboard = ReplyKeyboardMarkup(
                [[KeyboardButton(text=prod.name)] for prod in products],
                resize_keyboard=True,
            )
            await update.message.reply_text(
                f"Выбери товар категории «{category.name}»:",
                reply_markup=keyboard,
            )
            return

        # 2. пробуем как товар
        product = await sync_to_async(
            Product.objects.filter(name=text, is_active=True).first
        )()
        if not product:
            return

        tg_user = await self.get_or_create_telegram_user(user)
        await self.add_product_to_cart(tg_user, product)

        await update.message.reply_text(
            f"Товар «{product.name}» добавлен в корзину 🧺"
        )

    # ============== корзина ==============

    async def cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        tg_user = await sync_to_async(
            TelegramUser.objects.filter(
                telegram_id=user.id,
                phone_number__isnull=False,
            ).first
        )()
        if not tg_user:
            await update.message.reply_text("Сначала зарегистрируйся через /start 📲")
            return

        cart = await sync_to_async(
            lambda: Order.objects.filter(user=tg_user, status="cart")
            .prefetch_related("items__product")
            .first()
        )()
        if not cart or not cart.items.exists():
            await update.message.reply_text("Твоя корзина пуста 🧺")
            return

        lines = ["Твоя корзина:"]
        for item in cart.items.all():
            lines.append(
                f"• {item.product.name} x{item.quantity} = {item.total_price} сум"
            )
        lines.append(f"\nИтого: {cart.total_price} сум")

        await update.message.reply_text("\n".join(lines))
