# 🌍 Интеграция мультиязычности - ИНСТРУКЦИЯ

## ✅ Что уже сделано

### 1. Созданы файлы переводов
- ✅ `/src/locales/ru.js` - Русский язык
- ✅ `/src/locales/uz.js` - Узбекский язык  
- ✅ `/src/locales/en.js` - Английский язык

### 2. Создан контекст языка
- ✅ `/src/contexts/LanguageContext.jsx` - Контекст для управления языком

### 3. Добавлен провайдер в приложение
- ✅ `/src/main.jsx` - Добавлен `LanguageProvider`

---

## 🔧 Что нужно сделать дальше

### Шаг 1: Обновить SideMenu.jsx

**Файл:** `/Users/mac/Documents/NextJs_projects/ky_sushi_front/src/components/SideMenu.jsx`

**Изменения:**

1. **Добавить импорт:**
```jsx
import { useLanguage } from "../contexts/LanguageContext";
```

2. **Добавить в компонент:**
```jsx
const { language, changeLanguage, languages, t } = useLanguage();
const [isLanguageMenuOpen, setIsLanguageMenuOpen] = useState(false);
```

3. **Заменить блок "Язык" (строки 218-235):**
```jsx
{/* Язык */}
<div className="mb-2">
  <button
    type="button"
    onClick={() => setIsLanguageMenuOpen(!isLanguageMenuOpen)}
    className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl w-full text-left transition-all duration-200 ${
      theme === 'light'
        ? 'hover:bg-gray-100 active:bg-gray-200'
        : 'hover:bg-gray-700/50 active:bg-gray-700'
    }`}
  >
    <div className={`p-2 rounded-xl ${
      theme === 'light' ? 'bg-white text-gray-600' : 'bg-gray-700/50 text-gray-400'
    }`}>
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
      </svg>
    </div>
    <span className={`flex-1 font-medium ${
      theme === 'light' ? 'text-gray-800' : 'text-white'
    }`}>{t('profile.language')}</span>
    <div className="flex items-center gap-2">
      <span className={`text-sm ${
        theme === 'light' ? 'text-gray-500' : 'text-gray-400'
      }`}>
        {languages.find(l => l.code === language)?.flag}
      </span>
      <svg className={`w-4 h-4 transition-transform ${
        isLanguageMenuOpen ? 'rotate-180' : ''
      } ${theme === 'light' ? 'text-gray-400' : 'text-gray-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </div>
  </button>

  {/* Выпадающий список языков */}
  {isLanguageMenuOpen && (
    <div className={`mt-2 ml-4 mr-4 rounded-xl overflow-hidden ${
      theme === 'light' ? 'bg-gray-50' : 'bg-gray-800/30'
    }`}>
      {languages.map((lang) => (
        <button
          key={lang.code}
          type="button"
          onClick={() => {
            changeLanguage(lang.code);
            setIsLanguageMenuOpen(false);
          }}
          className={`flex items-center gap-3 px-4 py-3 w-full text-left transition-colors ${
            language === lang.code
              ? theme === 'light'
                ? 'bg-red-50 text-red-600'
                : 'bg-red-500/20 text-red-400'
              : theme === 'light'
                ? 'hover:bg-gray-100 text-gray-700'
                : 'hover:bg-gray-700/50 text-gray-300'
          }`}
        >
          <span className="text-xl">{lang.flag}</span>
          <span className="flex-1 font-medium">{lang.name}</span>
          {language === lang.code && (
            <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </button>
      ))}
    </div>
  )}
</div>
```

---

### Шаг 2: Обновить другие компоненты

Вот список компонентов, которые нужно обновить:

#### Cart.jsx
```jsx
import { useLanguage } from "../contexts/LanguageContext";

// В компоненте:
const { t } = useLanguage();

// Заменить тексты:
"Ваш заказ" → {t('cart.title')}
"Сумма заказа:" → {t('cart.itemsTotal')}
"Стоимость доставки:" → {t('cart.deliveryCost')}
"Бесплатно" → {t('common.free')}
"Оформить заказ" → {t('cart.checkout')}
"сум" → {t('common.sum')}
```

#### ProductCard.jsx
```jsx
import { useLanguage } from "../contexts/LanguageContext";

const { t } = useLanguage();

// Заменить:
"Добавить" → {t('menu.addToCart')}
"сум" → {t('common.sum')}
```

#### ProductModal.jsx
```jsx
import { useLanguage } from "../contexts/LanguageContext";

const { t } = useLanguage();

// Заменить:
"Свежее приготовление" → {t('product.preparationTime')}
"15-25 минут" → {t('product.preparationTimeValue')}
"Добавить в корзину" → {t('product.addToCart')}
"Оформить заказ" → {t('product.orderNow')}
"Количество:" → {t('checkout.quantity')}
"Итого" → {t('cart.total')}
"сум" → {t('common.sum')}
```

#### CheckoutModal.jsx
```jsx
import { useLanguage } from "../contexts/LanguageContext";

const { t } = useLanguage();

// Заменить все тексты на t('checkout.*')
```

#### CartDetails.jsx
```jsx
import { useLanguage } from "../contexts/LanguageContext";

const { t } = useLanguage();

// Заменить все тексты
```

---

## 📝 Примеры использования

### Простой текст:
```jsx
<h1>{t('menu.title')}</h1>
```

### Текст с переменными:
```jsx
<span>{t('cart.items')} {count}</span>
```

### Условный текст:
```jsx
{deliveryPrice > 0 
  ? `${deliveryPrice.toLocaleString("ru-RU")} ${t('common.sum')}`
  : t('common.free')
}
```

---

## 🧪 Тестирование

1. Откройте приложение
2. Откройте боковое меню
3. Нажмите на "Язык"
4. Выберите другой язык
5. Проверьте, что все тексты изменились

---

## ✅ Чек-лист

- [ ] Обновить SideMenu.jsx
- [ ] Обновить Cart.jsx
- [ ] Обновить ProductCard.jsx
- [ ] Обновить ProductModal.jsx
- [ ] Обновить CheckoutModal.jsx
- [ ] Обновить CartDetails.jsx
- [ ] Обновить Header.jsx
- [ ] Обновить BottomNav.jsx
- [ ] Протестировать все языки

---

**Следующий шаг:** Я обновлю SideMenu.jsx для вас
