from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    APP_TITLE: str = "Serviko API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str

    # Admin
    ADMIN_API_KEY: str

    # Auth recovery
    OTP_EXPIRY_SECONDS: int = 300
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_VERIFY_ATTEMPTS: int = 5
    OTP_LOCK_MINUTES: int = 15
    RECOVERY_RATE_LIMIT_WINDOW_SECONDS: int = 300
    RECOVERY_RATE_LIMIT_MAX_REQUESTS: int = 10
    SMS_PROVIDER: str = "stub"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # ZegoCloud (real-time communication)
    ZEGO_APP_ID: int = 0
    ZEGO_SERVER_SECRET: str = ""

    # Razorpay (Test Mode)
    RAZORPAY_MODE: str = "test"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_CURRENCY: str = "INR"

    # Supabase Storage
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET_PROFILE_IMAGES: str = "profile-images"
    SUPABASE_BUCKET_PROVIDER_DOCUMENTS: str = "provider-documents"
    SUPABASE_BUCKET_PROVIDER_BANNERS: str = "provider-banners"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
