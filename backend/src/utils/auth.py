import hashlib
import hmac
import random
import time
from typing import Dict, Any

from jose import jwt

from schemes.user import TokenPair
from settings import settings


def hash_code(code: str) -> str:
    return hmac.new(
        settings.otp.hash_salt.encode(),
        code.encode(),
        hashlib.sha256
    ).hexdigest()

def gen_code(n: int) -> str:
    return str(random.randint(0, 10**n - 1)).zfill(n)


def make_tokens(payload: Dict[str, Any]) -> TokenPair:
    now = int(time.time())
    access = jwt.encode(
        {**payload, "type":"access", "iat": now, "exp": now + settings.jwt.access_exp},
        settings.jwt.secret,
        algorithm=settings.jwt.alg
    )
    refresh = jwt.encode(
        {**payload, "type": "refresh", "iat": now, "exp": now + settings.jwt.refresh_exp},
        settings.jwt.secret,
        algorithm=settings.jwt.alg
    )
    return TokenPair(access_token=access, refresh_token=refresh)
