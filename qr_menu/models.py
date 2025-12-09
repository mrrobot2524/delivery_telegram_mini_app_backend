from django.db import models
from menu.models import Category, Product

class QROnlyCategory(models.Model):
    """
    Категория ТОЛЬКО для QR-меню. 
    Никак не связана с основным меню Telegram App.
    """
    name = models.CharField(max_length=255, verbose_name="Название категории")
    image = models.ImageField(upload_to="qr_categories/", blank=True, null=True, verbose_name="Изображение")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Сортировка")
    
    class Meta:
        verbose_name = "Категория (QR Only)"
        verbose_name_plural = "Категории (QR Only)"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

class QROnlyProduct(models.Model):
    """
    Товар ТОЛЬКО для QR-меню.
    """
    category = models.ForeignKey(QROnlyCategory, on_delete=models.CASCADE, related_name="products", verbose_name="Категория")
    name = models.CharField(max_length=255, verbose_name="Название товара")
    description = models.TextField(blank=True, verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    image = models.ImageField(upload_to="qr_products/", verbose_name="Фото", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    class Meta:
        verbose_name = "Товар (QR Only)"
        verbose_name_plural = "Товары (QR Only)"
    
    def __str__(self):
        return self.name

class QRTable(models.Model):
    """
    Столик для QR-меню.
    """
    import uuid
    number = models.CharField(max_length=50, unique=True, verbose_name="Номер столика")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    qr_code = models.ImageField(upload_to="qr_codes/tables/", blank=True, null=True, verbose_name="QR Код")
    
    # Связь с категориями, которые доступны на этом столе
    categories = models.ManyToManyField(QROnlyCategory, blank=True, verbose_name="Доступные категории")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Столик (QR)"
        verbose_name_plural = "Столики (QR)"
        
    def __str__(self):
        return f"Стол {self.number}"

    def save(self, *args, **kwargs):
        # Генерация QR-кода при сохранении
        if not self.qr_code:
            import qrcode
            from PIL import Image, ImageDraw, ImageFont
            from io import BytesIO
            from django.core.files import File
            
            # URL вашего приложения
            # domain = "https://crazy-worms-trade.loca.lt" 
            domain = "https://tss7pc8k-5173.euw.devtunnels.ms" 
            qr_url = f"{domain}/menu/{self.uuid}"
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
            
            # Дорисовка текста
            width, height = img.size
            new_height = height + 60 
            new_img = Image.new('RGB', (width, new_height), 'white')
            new_img.paste(img, (0, 0))
            draw = ImageDraw.Draw(new_img)
            
            try:
                font = ImageFont.truetype("Arial.ttf", 30)
            except IOError:
                font = ImageFont.load_default()
            
            text = f"Стол {self.number}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            
            x = (width - text_w) / 2
            y = height + (60 - (bbox[3] - bbox[1])) / 2 - 10
            
            draw.text((x, y), text, fill="black", font=font)
            
            buffer = BytesIO()
            new_img.save(buffer, format="PNG")
            
            file_name = f"qr_table_{self.number}_{self.uuid.hex[:4]}.png"
            self.qr_code.save(file_name, File(buffer), save=False)
            
        super().save(*args, **kwargs)
