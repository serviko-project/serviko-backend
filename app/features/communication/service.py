import json
import random
import time
import struct
import binascii

from Crypto.Cipher import AES

from app.core.config import get_settings

# Token validity: 24 hours
TOKEN_EFFECTIVE_TIME_SECONDS = 86400


class _TokenInfo:
    def __init__(self, token: str, error_code: int, error_message: str):
        self.token = token
        self.error_code = error_code
        self.error_message = error_message


def _make_nonce() -> int:
    return random.getrandbits(31)


def _make_random_iv() -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    return "".join(chars[int(random.random() * 16)] for _ in range(16))


def _aes_pkcs5_padding(cipher_text: str, block_size: int) -> str:
    padding_size = len(cipher_text.encode("utf-8"))
    padding = block_size - padding_size % block_size
    return cipher_text + chr(padding) * padding


def _aes_encrypt(plain_text: str, key: str, iv: str) -> bytes:
    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    content_padding = _aes_pkcs5_padding(plain_text, 16)
    return cipher.encrypt(content_padding.encode("utf-8"))


def _generate_token04(
    app_id: int,
    user_id: str,
    secret: str,
    effective_time_in_seconds: int,
    payload: str,
) -> _TokenInfo:
    if not isinstance(app_id, int) or app_id == 0:
        return _TokenInfo("", 1, "appID invalid")
    if not isinstance(user_id, str) or user_id == "":
        return _TokenInfo("", 3, "userID invalid")
    if not isinstance(secret, str) or len(secret) != 32:
        return _TokenInfo("", 5, "secret must be a 32 byte string")
    if not isinstance(effective_time_in_seconds, int) or effective_time_in_seconds <= 0:
        return _TokenInfo("", 6, "effective_time_in_seconds invalid")

    create_time = int(time.time())
    expire_time = create_time + effective_time_in_seconds
    nonce = _make_nonce()

    _token = {
        "app_id": app_id,
        "user_id": user_id,
        "nonce": nonce,
        "ctime": create_time,
        "expire": expire_time,
        "payload": payload,
    }
    plain_text = json.dumps(_token, separators=(",", ":"), ensure_ascii=False)
    iv = _make_random_iv()
    encrypt_buf = _aes_encrypt(plain_text, secret, iv)

    result_size = len(encrypt_buf) + 28
    result = bytearray(result_size)

    result[0:8] = struct.pack("!q", expire_time)
    result[8:10] = struct.pack("!h", len(iv))

    buffer = bytearray(iv.encode("utf-8"))
    result[10 : 10 + len(buffer)] = buffer[:]

    result[26:28] = struct.pack("!h", len(encrypt_buf))
    result[28 : 28 + len(encrypt_buf)] = encrypt_buf[:]

    token = "04" + binascii.b2a_base64(result, newline=False).decode()
    return _TokenInfo(token, 0, "success")


class CommunicationService:
    # Generates a Zego token for the given user
    def generate_token(self, user_id: str) -> dict:
        settings = get_settings()

        token_info = _generate_token04(
            app_id=settings.ZEGO_APP_ID,
            user_id=user_id,
            secret=settings.ZEGO_SERVER_SECRET,
            effective_time_in_seconds=TOKEN_EFFECTIVE_TIME_SECONDS,
            payload="",
        )

        if token_info.error_code != 0:
            raise ValueError(
                f"Failed to generate Zego token: {token_info.error_message}"
            )

        return {
            "token": token_info.token,
            "expires_in": TOKEN_EFFECTIVE_TIME_SECONDS,
        }
