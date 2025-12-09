# 🔧 Инструкция: Как исправить интеграцию акций (Promotions)

## ❌ Текущая проблема

Акции создаются в админке, но **НЕ применяются к ценам товаров** при добавлении в корзину.

**Пример:**
- Товар "Филадельфия" стоит 50,000 сум
- Создана акция: скидка 20%
- Ожидаемая цена в корзине: 40,000 сум
- **Реальная цена в корзине: 50,000 сум** ❌

---

## ✅ Решение (3 шага)

### Шаг 1: Добавить метод расчета цены со скидкой

**Файл:** `menu/models.py`

```python
from django.db import models

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["category", "name"]

    def __str__(self):
        return self.name
    
    # ⬇️ ДОБАВИТЬ ЭТОТ МЕТОД
    def get_discounted_price(self):
        """
        Получить цену с учетом активных акций.
        Если акций нет - возвращает обычную цену.
        """
        from django.utils import timezone
        from orders.models import Promotion
        
        # Находим активные акции для этого товара
        active_promotions = self.promotions.filter(
            is_active=True,
            valid_from__lte=timezone.now(),
            valid_until__gte=timezone.now()
        )
        
        # Если акций нет - возвращаем обычную цену
        if not active_promotions.exists():
            return self.price
        
        # Берем первую акцию (можно изменить логику на "самую выгодную")
        promo = active_promotions.first()
        
        # Рассчитываем скидку
        if promo.discount_type == 'percentage':
            discount = (self.price * promo.discount_value) / 100
            return self.price - discount
        else:  # fixed
            return max(self.price - promo.discount_value, 0)
    
    # ⬇️ ДОБАВИТЬ ЭТОТ МЕТОД
    def get_active_promotion(self):
        """
        Получить активную акцию для товара (если есть).
        """
        from django.utils import timezone
        from orders.models import Promotion
        
        return self.promotions.filter(
            is_active=True,
            valid_from__lte=timezone.now(),
            valid_until__gte=timezone.now()
        ).first()
```

---

### Шаг 2: Изменить логику добавления в корзину

**Файл:** `orders/views.py`

Найдите метод, где создается `OrderItem` (примерно строка 150-200):

**Было:**
```python
order_item, created = OrderItem.objects.get_or_create(
    order=cart,
    product=product,
    defaults={"price": product.price}  # ❌ Берется обычная цена
)
```

**Стало:**
```python
order_item, created = OrderItem.objects.get_or_create(
    order=cart,
    product=product,
    defaults={"price": product.get_discounted_price()}  # ✅ Берется цена с акцией!
)

# Если товар уже был в корзине, обновляем его цену
if not created:
    # Обновляем цену на случай, если акция изменилась
    order_item.price = product.get_discounted_price()
    order_item.save()
```

---

### Шаг 3: Обновить API (сериализатор)

**Файл:** `menu/serializers.py`

**Было:**
```python
class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "image", "category", "is_active"]
    
    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None
```

**Стало:**
```python
class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    image = serializers.SerializerMethodField()
    
    # ⬇️ ДОБАВИТЬ ЭТИ ПОЛЯ
    discounted_price = serializers.SerializerMethodField()
    has_promotion = serializers.SerializerMethodField()
    promotion_info = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "price", 
            "discounted_price",  # ← новое поле
            "has_promotion",     # ← новое поле
            "promotion_info",    # ← новое поле
            "image", "category", "is_active"
        ]
    
    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None
    
    # ⬇️ ДОБАВИТЬ ЭТИ МЕТОДЫ
    def get_discounted_price(self, obj):
        """Цена с учетом акции"""
        return obj.get_discounted_price()
    
    def get_has_promotion(self, obj):
        """Есть ли активная акция"""
        return obj.get_active_promotion() is not None
    
    def get_promotion_info(self, obj):
        """Информация об акции"""
        promo = obj.get_active_promotion()
        if not promo:
            return None
        
        return {
            "name": promo.name,
            "discount_type": promo.discount_type,
            "discount_value": float(promo.discount_value),
        }
```

---

## 🧪 Тестирование

### 1. Создайте акцию в админке

1. Откройте `/admin/orders/promotion/add/`
2. Заполните:
   - **Название:** "Скидка 20% на роллы"
   - **Тип скидки:** Процент
   - **Значение скидки:** 20
   - **Товары:** Выберите несколько роллов
   - **Период действия:** Сегодня - через неделю
   - **Активна:** ✅ Да
3. Сохраните

### 2. Проверьте API

Откройте в браузере:
```
http://localhost:8000/api/menu/products/?category_id=1
```

Должны увидеть:
```json
{
  "id": 1,
  "name": "Филадельфия",
  "price": "50000.00",
  "discounted_price": "40000.00",  // ← Новое поле!
  "has_promotion": true,            // ← Новое поле!
  "promotion_info": {               // ← Новое поле!
    "name": "Скидка 20% на роллы",
    "discount_type": "percentage",
    "discount_value": 20.0
  }
}
```

### 3. Проверьте корзину

1. Добавьте товар с акцией в корзину
2. Откройте `/admin/orders/order/`
3. Найдите свою корзину
4. Проверьте цену в `OrderItem` - должна быть со скидкой!

---

## 🎨 Бонус: Обновление фронтенда

**Файл:** `ky_sushi_front/src/components/ProductCard.jsx`

Добавьте отображение скидки:

```jsx
function ProductCard({ product, onAddToCart }) {
  return (
    <div className="product-card">
      <img src={product.image} alt={product.name} />
      <h3>{product.name}</h3>
      
      {/* ⬇️ ДОБАВИТЬ ЭТОТ БЛОК */}
      {product.has_promotion ? (
        <div className="price-block">
          <span className="old-price">{product.price} сум</span>
          <span className="new-price">{product.discounted_price} сум</span>
          <span className="discount-badge">
            {product.promotion_info.name}
          </span>
        </div>
      ) : (
        <div className="price-block">
          <span className="price">{product.price} сум</span>
        </div>
      )}
      
      <button onClick={() => onAddToCart(product.id)}>
        В корзину
      </button>
    </div>
  );
}
```

**CSS:**
```css
.old-price {
  text-decoration: line-through;
  color: #999;
  font-size: 14px;
}

.new-price {
  color: #e74c3c;
  font-weight: bold;
  font-size: 18px;
  margin-left: 8px;
}

.discount-badge {
  background: #e74c3c;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  margin-left: 8px;
}
```

---

## ✅ Готово!

После этих изменений:
- ✅ Акции будут автоматически применяться к ценам
- ✅ Фронтенд будет показывать старую и новую цену
- ✅ В корзине будет цена со скидкой
- ✅ В админке будет видно, какая цена была применена

---

**Важно:** После изменения моделей не забудьте:
```bash
python manage.py makemigrations
python manage.py migrate
```

(Хотя в данном случае миграции не нужны, т.к. мы только добавили методы, а не поля)
