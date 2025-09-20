import json

from datetime import timedelta, timezone, datetime
from fastapi import APIRouter, HTTPException, Request, Depends

from orm.models import User, PhoneOTP
from schemes.auth import PhoneIn, VerifyIn, RefreshIn, TokenPair
from settings import settings
from utils.auth import make_token, gen_code, hash_code, decode_refresh_token
from redis.asyncio import Redis


router = APIRouter(prefix="/auth", tags=["auth"])


def get_redis(request: Request) -> Redis:
    r = getattr(request.app.state, "redis", None)
    if r is None:
        raise HTTPException(500, "Redis not initialized")
    return r


async def send_sms(redis: Redis, payload: dict) -> bool:
    if settings.app.debug:
        return not print("[DEV SMS] {phone_number}: {verification_code}".format(**payload))
    return not await redis.publish(settings.app.bluetooth_channel, json.dumps(payload))


@router.post("/request")
async def request_code(body: PhoneIn, r: Redis = Depends(get_redis)):
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

    response = await send_sms(r, payload={"phone_number": phone, "verification_code": code})
    return {"ok": response}


@router.post("/verify")
async def verify_code(body: VerifyIn) -> TokenPair:
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

    payload = {"sub": str(user.id)}
    return TokenPair(
        access=make_token(payload, "access"),
        refresh=make_token(payload, "refresh"),
    )


@router.post("/refresh")
async def refresh_token(body: RefreshIn) -> TokenPair:
    try:
        payload = decode_refresh_token(body.refresh)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    sub = payload.get("sub")
    if not sub and not sub.isdigit():
        raise HTTPException(status_code=401, detail="invalid token payload")

    user = await User.get_or_none(id=int(sub))
    if not user:
        raise HTTPException(status_code=401, detail="user not found")

    payload = {"sub": str(user.id)}
    return TokenPair(
        access=make_token(payload, "access"),
        refresh=body.refresh,
    )

