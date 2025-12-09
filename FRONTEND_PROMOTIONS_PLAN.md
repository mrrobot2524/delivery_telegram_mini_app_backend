# 🎨 План интеграции акций во фронтенд

## 📊 Текущая ситуация

### ✅ Что уже работает (бэкенд):
- API возвращает поля: `discounted_price`, `has_promotion`, `promotion_info`
- Цена в корзине сохраняется со скидкой
- Акции применяются автоматически

### ❌ Что НЕ работает (фронтенд):
- Компоненты используют только `product.price`
- Нет отображения зачеркнутой цены
- Нет бейджа "Акция"
- Пользователь не видит, что товар со скидкой

---

## 🎯 Компоненты для обновления

### 1. ProductCard.jsx ⚠️
**Проблема:** Показывает только `product.price`

**Что нужно:**
- Проверять `product.has_promotion`
- Показывать зачеркнутую старую цену
- Показывать новую цену `product.discounted_price`
- Добавить бейдж "Акция"

**Строки для изменения:**
- Строка 121-125: Цена на изображении

---

### 2. ProductModal.jsx ⚠️
**Проблема:** Показывает только `product.price`

**Что нужно:**
- Показывать зачеркнутую старую цену
- Показывать новую цену со скидкой
- Добавить информацию об акции

**Строки для изменения:**
- Строка 102-107: Цена в шапке
- Строка 168: Итого в корзине
- Строка 187: Кнопка "Оформить заказ"
- Строка 206: Кнопка "Добавить в корзину"

---

### 3. CartDetails.jsx ⚠️
**Проблема:** Рассчитывает сумму по `item.product.price`

**Что нужно:**
- Использовать `item.price` (цена уже со скидкой из бэкенда)

**Строки для изменения:**
- Строка 110: Расчет суммы корзины
- Строка 336: Отображение цены товара

---

### 4. CheckoutModal.jsx ⚠️
**Проблема:** Показывает `item.product.price`

**Что нужно:**
- Использовать `item.price` (цена со скидкой)

**Строки для изменения:**
- Строка 620: Отображение цены товара

---

## 🎨 Дизайн акций

### Вариант 1: Минималистичный
```jsx
{product.has_promotion ? (
  <div className="flex items-center gap-2">
    <span className="text-gray-400 line-through text-sm">
      {product.price?.toLocaleString("ru-RU")} сум
    </span>
    <span className="text-red-500 font-bold">
      {product.discounted_price?.toLocaleString("ru-RU")} сум
    </span>
  </div>
) : (
  <span className="font-bold">
    {product.price?.toLocaleString("ru-RU")} сум
  </span>
)}
```

### Вариант 2: С бейджем (рекомендуется)
```jsx
{product.has_promotion ? (
  <div className="relative">
    {/* Бейдж "Акция" */}
    <div className="absolute -top-2 -right-2 bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
      АКЦИЯ
    </div>
    
    {/* Цены */}
    <div className="flex flex-col">
      <span className="text-gray-400 line-through text-xs">
        {product.price?.toLocaleString("ru-RU")} сум
      </span>
      <span className="text-red-500 font-bold text-lg">
        {product.discounted_price?.toLocaleString("ru-RU")} сум
      </span>
    </div>
  </div>
) : (
  <span className="font-bold text-lg">
    {product.price?.toLocaleString("ru-RU")} сум
  </span>
)}
```

### Вариант 3: С процентом скидки
```jsx
{product.has_promotion ? (
  <div className="relative">
    {/* Процент скидки */}
    {product.promotion_info?.discount_type === 'percentage' && (
      <div className="absolute -top-2 -right-2 bg-gradient-to-r from-red-600 to-red-500 text-white text-xs font-bold px-2 py-1 rounded-full shadow-lg">
        -{product.promotion_info.discount_value}%
      </div>
    )}
    
    {/* Цены */}
    <div className="flex items-baseline gap-2">
      <span className="text-gray-400 line-through text-sm">
        {product.price?.toLocaleString("ru-RU")}
      </span>
      <span className="text-red-500 font-bold text-xl">
        {product.discounted_price?.toLocaleString("ru-RU")} сум
      </span>
    </div>
  </div>
) : (
  <span className="font-bold text-xl">
    {product.price?.toLocaleString("ru-RU")} сум
  </span>
)}
```

---

## 📝 Порядок исправлений

### Шаг 1: ProductCard.jsx (5 минут)
- Добавить проверку `has_promotion`
- Показать зачеркнутую цену и новую цену
- Добавить бейдж "АКЦИЯ"

### Шаг 2: ProductModal.jsx (5 минут)
- Обновить отображение цены в шапке
- Обновить расчет итоговой суммы
- Добавить информацию об акции

### Шаг 3: CartDetails.jsx (3 минуты)
- Использовать `item.price` вместо `item.product.price`

### Шаг 4: CheckoutModal.jsx (2 минуты)
- Использовать `item.price` вместо `item.product.price`

**Общее время: ~15 минут**

---

## ✅ Ожидаемый результат

### До:
```
Филадельфия
50,000 сум
[Добавить]
```

### После:
```
Филадельфия        [АКЦИЯ -20%]
50,000 сум (зачеркнуто)
40,000 сум (красным, жирным)
[Добавить]
```

---

## 🧪 Тестирование

1. Создать акцию в админке
2. Открыть фронтенд
3. Проверить:
   - ✅ Карточка товара показывает скидку
   - ✅ Модальное окно показывает скидку
   - ✅ Корзина показывает правильную цену
   - ✅ Checkout показывает правильную цену

---

**Готово к исправлению!**
