from datetime import timedelta, timezone, datetime
from fastapi import APIRouter, HTTPException

from orm.models import User, PhoneOTP
from schemes.auth import PhoneIn, VerifyIn
from settings import settings
from utils.auth import make_tokens, gen_code, hash_code

router = APIRouter(prefix="/auth", tags=["auth"])


def send_sms(phone: str, text: str) -> None:
    if settings.app.debug:
        return print(f"[DEV SMS] {phone}: {text}")
    pass


@router.post("/request")
async def request_code(body: PhoneIn):
    phone, now_utc = body.phone, datetime.now(timezone.utc)
    otp = await PhoneOTP.get_or_none(phone=phone)

    if otp and not otp.can_resend:
        raise HTTPException(429, "too many requests, wait before resend")

    code = gen_code(settings.otp.length)
    code_h = hash_code(code)
    expires = now_utc + timedelta(minutes=settings.otp.ttl_min)

    if otp:
        otp.code_hash = code_h
        otp.expires_at = expires
        otp.attempts = 0
        otp.last_sent_at = now_utc
        await otp.save()
    else:
        await PhoneOTP.create(
            phone=phone,
            code_hash=code_h,
            expires_at=expires,
            attempts=0,
            last_sent_at=now_utc,
        )

    send_sms(phone, f"Ваш код: {code}")
    return {"ok": True}


@router.post("/verify")
async def verify_code(body: VerifyIn):
    phone, code, now_utc = body.phone, body.code, datetime.now(timezone.utc)
    otp = await PhoneOTP.get_or_none(phone=phone)
    if not otp:
        raise HTTPException(400, "request code first")

    if otp.is_expired:
        await otp.delete()
        raise HTTPException(400, "code expired")

    if otp.attempts >= settings.otp.max_attempts:
        await otp.delete()
        raise HTTPException(429, "too many attempts")

    if otp.code_hash != hash_code(code):
        otp.attempts += 1
        await otp.save()
        raise HTTPException(400, "invalid code")

    await otp.delete()

    user = await User.get_or_none(phone=phone)
    if not user:
        user = await User.create(phone=phone, phone_verified_at=now_utc)

    tokens = make_tokens({"sub": user.id})
    return tokens