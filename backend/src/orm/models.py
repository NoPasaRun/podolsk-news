from datetime import datetime, timezone

from tortoise import fields
from tortoise.models import Model

from settings import settings


class User(Model):
    id = fields.IntField(pk=True)
    phone = fields.CharField(max_length=32, unique=True, null=True)
    phone_verified_at = fields.DatetimeField(null=True)
    name = fields.CharField(max_length=255, null=True)
    avatar = fields.CharField(max_length=512, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class PhoneOTP(Model):
    id = fields.IntField(pk=True)
    phone = fields.CharField(max_length=32, index=True)
    code_hash = fields.CharField(max_length=128)
    expires_at = fields.DatetimeField()
    attempts = fields.IntField(default=0)
    last_sent_at: datetime = fields.DatetimeField(null=True)

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def can_resend(self) -> bool:
        if not self.last_sent_at:
            return True
        delta = (datetime.now(timezone.utc) - self.last_sent_at).total_seconds()
        return delta >= settings.otp.resend_sec

    class Meta:
        table = "phone_otps"
        indexes = (("phone",),)
