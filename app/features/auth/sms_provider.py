import logging
from abc import ABC, abstractmethod

from app.core.config import Settings

logger = logging.getLogger(__name__)


class SmsProvider(ABC):
    @abstractmethod
    async def send_otp(self, phone_e164: str, otp_code: str) -> None:
        pass


class StubSmsProvider(SmsProvider):
    async def send_otp(self, phone_e164: str, otp_code: str) -> None:
        logger.info(
            "sms_otp_stub_sent phone=%s otp=%s",
            phone_e164,
            otp_code,
        )


def get_sms_provider(settings: Settings) -> SmsProvider:
    if settings.SMS_PROVIDER.lower() == "stub":
        return StubSmsProvider()

    logger.warning(
        "Unknown SMS provider '%s', falling back to stub",
        settings.SMS_PROVIDER,
    )
    return StubSmsProvider()
