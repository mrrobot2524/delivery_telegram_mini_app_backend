# Sushi Telegram Mini App

Телеграм‑мини‑приложение для заказа суши.  
Фронтенд на React + Vite, бэкенд на Django REST Framework, отдельный Telegram‑бот, который открывает мини‑приложение и передаёт `initData`.

---

## Возможности

- Просмотр меню по категориям
- Добавление товаров в корзину из карточек и модалки товара
- Управление количеством в корзине (плюс/минус)
- Выбор типа заказа: самовывоз или доставка
- Выбор адреса доставки на карте или пункта самовывоза
- Оформление заказа с комментарием
- Активный заказ:
  - статус (`new`, `in_progress`, `done`, `canceled`)
  - время готовности (строка от бэка)
  - адрес доставки / самовывоза
  - список позиций с фото и ценой
  - кнопка отказа от отдельного товара
- История заказов пользователя
- Интеграция с Telegram Mini App через `X-Telegram-Init-Data`

---

## Стек

**Фронтенд**

- React + Vite  
- React Router v6  
- Tailwind CSS  
- React Icons  
- Telegram WebApp API (MainButton, initData)

**Бэкенд**

- Django  
- Django REST Framework  
- PostgreSQL (или другая совместимая БД)  
- Модели: `TelegramUser`, `Product`, `Order`, `OrderItem`

**Бот**

- Python + `python-telegram-bot` / `aiogram` (любой фреймворк)  
- WebApp‑кнопка, которая открывает мини‑приложение по URL фронта  
- Передача `initData` в заголовке `X-Telegram-Init-Data` с фронта на бэкенд

---

## Архитектура заказов

`Order.status`:

- `cart` – корзина (неоформленный заказ)  
- `new` – только что оформленный заказ  
- `in_progress` – заказ готовится  
- `done` – доставлен / завершён  
- `canceled` – отменён  

`Order.delivery_type`:

- `pickup` – самовывоз  
- `delivery` – доставка  

**Корзина и активный заказ**

- корзина: `Order` со статусом `cart`;  
- активный заказ: последний `Order` этого пользователя со статусом `new` или `in_progress`.

Эндпоинт корзины всегда возвращает:

{
"cart": { ... } | null,
"active_order": { ... } | null
}



---

## Бэкенд

Модели, сериализаторы и вьюхи уже приведены выше — проект использует:

- `Order` / `OrderItem` (одна модель и для корзины, и для заказов);  
- сериализатор `CartWithActiveSerializer`, возвращающий `cart` и `active_order`;  
- `CartView`, `CartItemView`, `CheckoutView`, `MyOrdersView`, `DeleteMyOrderView`.

---

## Фронтенд

Основные страницы:

- `MenuPage` — список категорий и товаров, модалка товара, снизу компактный блок корзины и переход в `/orders`.  
- `OrdersPage` — блок активного заказа + корзина + выбор доставки и адреса + кнопка «Оформить • сумма».

Работа с API корзины строится вокруг ответа `{cart, active_order}`.

---

## Telegram‑бот

### Требования

- У бота должен быть настроен WebApp‑URL в BotFather:  
  `t.me/<botname>/app?startapp=<payload>` (или кнопка WebApp в inline‑клавиатуре).
- Фронтенд должен быть доступен по HTTPS (обязательное требование Telegram).

### Пример кода бота (Python + aiogram)

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL") # например https://example.com/

bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
kb = types.InlineKeyboardMarkup()
kb.add(
types.InlineKeyboardButton(
text="Открыть меню",
web_app=types.WebAppInfo(url=WEBAPP_URL)
)
)
await message.answer("Добро пожаловать! Откройте мини‑приложение:", reply_markup=kb)

if name == "main":
executor.start_polling(dp, skip_updates=True)



### Как `initData` попадает на бэкенд

1. В мини‑приложении (фронт) через `window.Telegram.WebApp.initData` берётся строка `initData`.  
2. При каждом запросе к бэкенду фронт кладёт её в заголовок:

await fetch("/api/orders/cart/", {
method: "GET",
headers: {
"X-Telegram-Init-Data": window.Telegram.WebApp.initData,
},
});



3. На бэкенде `MiniAppUserMixin` читает заголовок `X-Telegram-Init-Data`, валидирует его через `validate_init_data` и находит/создаёт `TelegramUser`.

---

## Запуск

### Бэкенд

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000



### Фронтенд

cd frontend
npm install
npm run dev # для разработки
npm run build # прод сборка



Укажи адрес бэкенда в `VITE_API_BASE_URL`.

### Бот

export BOT_TOKEN="ВАШ_ТОКЕН"
export WEBAPP_URL="https://ваш-домен-с-мини-аппом/"
python  manage.py runbot.py

Bot in telegram_users/management/commonds/runbot.py

(или аналогичная команда для фреймворка, который используешь.)

---

## Переменные окружения

**Бэкенд**

- `SECRET_KEY`
- `DEBUG`
- `DATABASE_URL` (или отдельные `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`)

**Фронтенд**

- `VITE_API_BASE_URL` — базовый URL бэкенда
- `VITE_TG_BOT_ID` / `VITE_TG_BOT_NAME` (если нужны в интерфейсе)

**Бот**

- `BOT_TOKEN` — токен Telegram‑бота  
- `WEBAPP_URL` — публичный HTTPS‑URL фронтенда

---

## Дальнейшие улучшения

- WebSocket/long polling для живого обновления статусов активного заказа  
- Подтверждение отказа от товаров в активном заказе  
- Промокоды и акции  
- Множественные адреса пользователя  
- Панель оператора/админа для управления заказами в реальном времени