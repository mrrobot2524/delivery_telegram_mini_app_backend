from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=255)          # Холодные роллы
    slug = models.SlugField(unique=True)             # holodnye-rolly
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=255)          # Запечённые роллы с угрём
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/") # фото товара [web:146][web:152]
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["category", "name"]

    def __str__(self):
        return self.name
