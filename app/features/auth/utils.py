import hashlib
import hmac
import re
import secrets

from app.features.auth.exceptions import WeakPasswordException


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_phone_e164(phone: str) -> str | None:
    raw = phone.strip()
    digits = re.sub(r"\D", "", raw)

    if len(digits) == 10:
        return f"+91{digits}"

    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"

    return None


def hash_otp(otp_code: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        otp_code.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return f"{salt}${digest}"


def verify_otp(otp_code: str, otp_hash: str) -> bool:
    try:
        salt, expected = otp_hash.split("$", maxsplit=1)
    except ValueError:
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        otp_code.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return hmac.compare_digest(digest, expected)


def mask_email(email: str) -> str:
    local, domain = email.split("@", maxsplit=1)
    if len(local) <= 1:
        local_mask = "*"
    else:
        local_mask = f"{local[0]}***"
    return f"{local_mask}@{domain}"


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        digits = f"91{digits}"
    elif len(digits) >= 12 and digits.startswith("91"):
        digits = digits[:12]

    last4 = digits[-4:] if len(digits) >= 4 else "0000"
    return f"+91******{last4}"


def validate_password_policy(password: str) -> None:
    if len(password) < 6:
        raise WeakPasswordException()
