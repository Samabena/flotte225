from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    SHOW_DOCS: bool = True

    # Database
    DATABASE_URL: str

    # CORS
    CORS_ORIGINS: str = "http://localhost:8000"

    # Email (SMTP)
    SMTP_HOST: str = "smtp.hostinger.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # Google Maps
    GOOGLE_MAPS_API_KEY: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def frontend_url(self) -> str:
        return self.cors_origins_list[0]

    class Config:
        env_file = ".env"


settings = Settings()
