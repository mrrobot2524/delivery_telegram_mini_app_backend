# ✅ Система уведомлений обновлена

**Дата:** 2025-12-08  
**Время:** 19:10

---

## 🔄 Что изменено:

Мы объединили два потока уведомлений в одном окне `NotificationsModal`:

1. **📢 Общие уведомления (Global Notifications):**
   - Акции
   - Новости
   - Информация для всех
   - *Источник:* `/api/content/notifications/`

2. **👤 Личные уведомления (User Notifications):**
   - Статусы ваших заказов ("Готовится", "Едет")
   - Результаты отмены заказов (Одобрено/Отклонено)
   - *Источник:* `/api/content/user-notifications/` (требует Telegram ID)

---

## 🛠️ Как это работает технически:

В `src/components/NotificationsModal.jsx`:

```javascript
// 1. Загружаем оба списка параллельно
const promises = [
  apiFetch("/api/content/notifications/"),
  telegramId ? fetchUserNotifications(telegramId) : null
];

// 2. Объединяем результаты
const allNotifications = [...globalNotifs, ...userNotifs];

// 3. Сортируем по времени (новые сверху)
allNotifications.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
```

---

## 📊 Результат для пользователя:

Пользователь открывает колокольчик и видит **единую ленту событий**:
- Сверху: "Ваш заказ принят!" (Личное)
- Ниже: "Акция: Ролл в подарок!" (Общее)
- Еще ниже: "Заказ доставлен" (Вчерашнее личное)

**Все важные сообщения теперь в одном месте!** 🚀
