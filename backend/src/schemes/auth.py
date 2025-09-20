from pydantic import BaseModel, field_validator

from settings import settings


class PhoneIn(BaseModel):

    phone: str
    @field_validator("phone")
    @classmethod
    def norm_e164(cls, v: str) -> str:
        v = v.strip().replace(" ", "")
        if not v.startswith("+") or not v[1:].isdigit():
            raise ValueError("phone must be in E.164, e.g. +4917612345678")
        if len(v) > 32:
            raise ValueError("phone too long")
        return v


class VerifyIn(PhoneIn):

    code: str
    @field_validator("code")
    @classmethod
    def only_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("code must be digits")
        return v


class TokenPair(BaseModel):
    access: str
    refresh: str
    access_expires_in: int = settings.jwt.access_exp
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh: str
    token_type: str = "bearer"
