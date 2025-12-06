import os
from celery import Celery

# Устанавливаем настройки Django по умолчанию для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Используем строку here, чтобы worker не должен был сериализовать
# объект конфигурации для дочерних процессов.
# namespace='CELERY' означает, что все настройки Celery должны иметь префикс CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Force Broker Configuration
# Так как Celery упорно игнорирует настройки из settings.py на локальной машине
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app.conf.update(
    broker_url='filesystem://',
    broker_transport_options={
        'data_folder_in': os.path.join(BASE_DIR, 'broker', 'in'),
        'data_folder_out': os.path.join(BASE_DIR, 'broker', 'out'),
        'data_folder_processed': os.path.join(BASE_DIR, 'broker', 'processed'),
    },
    result_backend='django-db',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tashkent',
    enable_utc=True,
)

# Автоматически находим задачи в файлах tasks.py каждого приложения
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
