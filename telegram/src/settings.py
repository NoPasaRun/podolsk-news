from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = Field("redis://redis:6379/0", alias="REDIS_URL")
    redis_in_channel: str = Field("redis_in_channel", alias="REDIS_IN_CHANNEL")
    redis_out_channel: str = Field("redis_out_channel", alias="REDIS_OUT_CHANNEL")

    tg_api_id: int = Field(..., alias="TG_API_ID")
    tg_api_hash: str = Field(..., alias="TG_API_HASH")
    tg_phone: str = Field(..., alias="TG_PHONE")
    tg_session: str = Field("telegram_crawler_session", alias="TG_SESSION")

    crawl_interval_sec: int = Field(60, alias="CRAWL_INTERVAL_SEC")
    tg_fetch_limit: int = Field(50, alias="TG_FETCH_LIMIT")

    user: str = Field(..., alias="POSTGRES_USER")
    password: str = Field(..., alias="POSTGRES_PASSWORD")
    name: str = Field(..., alias="POSTGRES_DB")

    @property
    def db_url(self):
        return f"postgresql://{self.user}:{self.password}@db:5432/{self.name}"


settings = Settings()
