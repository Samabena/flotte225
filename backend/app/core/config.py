from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    SHOW_DOCS: bool = True

    # Database
    DATABASE_URL: str

    # CORS
    CORS_ORIGINS: str = "http://localhost:8000"

    # Email (SendGrid)
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@flotte225.ci"

    # AI Reports (OpenRouter)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "mistralai/mistral-large"

    # WhatsApp (Meta Cloud API)
    WHATSAPP_API_URL: str = ""
    WHATSAPP_TOKEN: str = ""

    # Webhook
    WEBHOOK_URL: str = ""
    WEBHOOK_INTERVAL_HOURS: int = 24

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
