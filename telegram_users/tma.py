import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from django.conf import settings


def validate_init_data(init_data: str, max_age: int = 86400):
    """
    Валидирует initData по алгоритму Telegram Mini Apps.
    Возвращает dict (со словарём user внутри) или None, если подпись/срок неверны. [web:348][web:357]
    """
    if not init_data:
        print("validate_init_data: empty init_data")
        return None

    try:
        data = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as e:
        print("validate_init_data: parse_qsl error:", e)
        return None

    hash_value = data.pop("hash", None)
    if not hash_value:
        print("validate_init_data: no hash in init_data")
        return None

    # формируем data_check_string
    data_check_arr = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(data_check_arr)

    # секретный ключ = HMAC_SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        key="WebAppData".encode(),
        msg=settings.TELEGRAM_BOT_TOKEN.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    # считаем контрольную подпись
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if calculated_hash != hash_value:
        print("validate_init_data: hash mismatch")
        return None

    # проверяем давность auth_date
    auth_date = int(data.get("auth_date", "0"))
    if max_age and (time.time() - auth_date > max_age):
        print("validate_init_data: auth_date is too old")
        return None

    # user — JSON-строка
    user_json = data.get("user")
    if user_json:
        try:
            data["user"] = json.loads(user_json)
        except json.JSONDecodeError as e:
            print("validate_init_data: user json error:", e)
            return None

    return data
