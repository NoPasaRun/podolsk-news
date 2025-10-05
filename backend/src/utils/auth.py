import hashlib
import hmac
import random
import time
from typing import Dict, Any, Optional, Type

from fastapi import Depends, HTTPException, WebSocketException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from fastapi.websockets import WebSocket

from orm.models import User
from settings import settings


def hash_code(code: str) -> str:
    return hmac.new(
        settings.otp.hash_salt.encode(),
        code.encode(),
        hashlib.sha256
    ).hexdigest()

def gen_code(n: int) -> str:
    return str(random.randint(0, 10**n - 1)).zfill(n)


def make_token(payload: Dict[str, Any], typ: str) -> str:
    now, exp_in = int(time.time()), getattr(settings.jwt, f"{typ}_exp")
    return jwt.encode(
        {**payload, "typ": typ, "iat": now, "exp": now + exp_in},
        settings.jwt.secret,
        algorithm=settings.jwt.alg
    )


def decode_refresh_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt.secret,
            algorithms=[settings.jwt.alg],
            options={"verify_aud": False},
        )
    except JWTError:
        raise ValueError("invalid token")

    if payload.get("typ") != "refresh":
        raise ValueError("token is not refresh")

    return payload


security = HTTPBearer(auto_error=False)


async def get_user(
        token: str,
        exception_class: Type[Exception] = HTTPException,
        **kwargs
) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.jwt.secret,
            algorithms=[settings.jwt.alg],
            options={"verify_aud": False},
        )
    except JWTError:
        WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        raise exception_class(**kwargs)

    if payload.get("typ") != "access":
        raise exception_class(**kwargs)

    sub = payload.get("sub")
    if not sub:
        raise exception_class(**kwargs)

    user = await User.get_or_none(id=sub)
    if not user:
        raise exception_class(**kwargs)

    return user


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="auth required")

    return await get_user(
        creds.credentials,
        status_code=status.HTTP_403_FORBIDDEN,
        detail="forbidden"
    )


def parse_bearer(auth: Optional[str]) -> Optional[str]:
    if not auth: return None
    if auth.lower().startswith("bearer, "):
        return auth.replace("bearer, ", "")
    return None


async def get_current_user_ws(websocket: WebSocket) -> User:
    token = parse_bearer(websocket.headers.get("sec-websocket-protocol"))
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    return await get_user(
        token, WebSocketException,
        code=status.WS_1008_POLICY_VIOLATION,
        reason="forbidden"
    )


async def get_optional_user(
        creds: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[User]:
    try:
        return await get_current_user(creds)
    except HTTPException:
        return None

