from base64 import b64encode, b64decode
from datetime import datetime

from fastapi import HTTPException


def make_cursor(dt: datetime, id_: int) -> str:
    return b64encode(f"{dt.isoformat()}|{id_}".encode()).decode()

def parse_cursor(cur: str) -> tuple[datetime, int]:
    try:
        raw = b64decode(cur.encode()).decode()
        sdt, sid = raw.split("|", 1)
        return datetime.fromisoformat(sdt), int(sid)
    except Exception:
        raise HTTPException(400, "Bad cursor")
