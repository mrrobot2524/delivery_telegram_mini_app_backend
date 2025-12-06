import hashlib
from django.conf import settings


def verify_click_signature(params, action):
    """
    Проверка MD5 подписи от Click
    
    Args:
        params: Параметры запроса от Click
        action: 0 для Prepare, 1 для Complete
    
    Returns:
        bool: True если подпись верна
    """
    if action == 0:  # Prepare
        sign_string = (
            f"{params['click_trans_id']}"
            f"{params['service_id']}"
            f"{settings.CLICK_SECRET_KEY}"
            f"{params['merchant_trans_id']}"
            f"{params['amount']}"
            f"{params['action']}"
            f"{params['sign_time']}"
        )
    else:  # Complete
        sign_string = (
            f"{params['click_trans_id']}"
            f"{params['service_id']}"
            f"{settings.CLICK_SECRET_KEY}"
            f"{params['merchant_trans_id']}"
            f"{params.get('merchant_prepare_id', '')}"
            f"{params['amount']}"
            f"{params['action']}"
            f"{params['sign_time']}"
        )
    
    calculated_sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    return calculated_sign == params.get('sign_string', '')


def get_click_error_message(error_code):
    """Получить описание ошибки Click по коду"""
    error_messages = {
        0: "Успешно",
        -1: "Неверная подпись",
        -2: "Неверная сумма",
        -3: "Неверное действие",
        -4: "Уже оплачено",
        -5: "Заказ не найден",
        -6: "Транзакция не найдена",
        -7: "Ошибка обновления",
        -8: "Неверный запрос",
        -9: "Отмена платежа",
    }
    return error_messages.get(error_code, f"Неизвестная ошибка ({error_code})")
