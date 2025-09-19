from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# ---------- APP ----------
class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    env: str = Field("dev", alias="ENV")
    secret: str = Field(..., alias="APP_SECRET")
    url: str = Field("http://localhost", alias="PUBLIC_ORIGIN")

    @property
    def debug(self) -> bool:
        return self.env == "dev"

# ---------- DB ----------
class DBSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    user: str = Field(..., alias="POSTGRES_USER")
    password: str = Field(..., alias="POSTGRES_PASSWORD")
    name: str = Field(..., alias="POSTGRES_DB")

    @property
    def url(self):
        return f"asyncpg://{self.user}:{self.password}@db:5432/{self.name}"

# ---------- JWT ----------
class JWTSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    secret: str = Field(..., alias="JWT_SECRET")
    alg: str = Field("HS256", alias="JWT_ALG")
    access_exp: int = Field(3600, alias="JWT_ACCESS_EXP")
    refresh_exp: int = Field(60 * 60 * 24 * 30, alias="JWT_REFRESH_EXP")

# ---------- OTP / PHONE LOGIN ----------
class OTPSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    ttl_min: int = Field(10, alias="OTP_TTL_MIN")
    length: int = Field(6, alias="OTP_LENGTH")
    resend_sec: int = Field(60, alias="OTP_RESEND_SEC")
    max_attempts: int = Field(5, alias="OTP_MAX_ATTEMPTS")
    hash_salt: str = Field(..., alias="OTP_HASH_SALT")


class Settings:
    app = AppSettings()
    db = DBSettings()
    jwt = JWTSettings()
    otp = OTPSettings()


settings = Settings()
