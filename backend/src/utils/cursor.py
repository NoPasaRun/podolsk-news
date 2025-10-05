from datetime import datetime, timezone
from typing import Tuple


def _to_utc(dt: datetime) -> datetime:
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        # если в БД timestamp without time zone — считаем, что это уже UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _to_micros(dt: datetime) -> int:
    dt = _to_utc(dt)
    # микросекунды с эпохи — без потери точности
    return int(dt.timestamp() * 1_000_000)

def _from_micros(us: int) -> datetime:
    return datetime.fromtimestamp(us / 1_000_000, tz=timezone.utc)

# --- recent: (last_pub_us, id) ---

def make_cursor_recent(last_pub: datetime, cid: int) -> str:
    return f"{_to_micros(last_pub)}:{cid}"

def parse_cursor_recent(s: str) -> Tuple[int, int]:
    us_s, cid_s = s.split(":")
    return int(us_s), int(cid_s)

# --- weight: (weight, last_pub_us, id) ---

def make_cursor_weight(weight: int, last_pub: datetime, cid: int) -> str:
    return f"{int(weight)}:{_to_micros(last_pub)}:{cid}"

def parse_cursor_weight(s: str) -> Tuple[int, int, int]:
    w_s, us_s, cid_s = s.split(":")
    return int(w_s), int(us_s), int(cid_s)