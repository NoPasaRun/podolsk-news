from typing import Optional


def normalize_handle(domain: str) -> Optional[str]:
    if not domain:
        return None
    d = domain.strip()
    if d.startswith("http"):
        for cut in ("https://t.me/s/", "http://t.me/s/", "https://t.me/", "http://t.me/"):
            if d.startswith(cut):
                d = d[len(cut):]
                break
        d = d.split("?")[0].strip("/")
    if d.startswith("@"):
        d = d[1:]
    d = d.split("/")[0]
    return d or None

def make_post_url(username: str, msg_id: int) -> str:
    return f"https://t.me/{username}/{msg_id}"

def first_line(text: str) -> str:
    return (text or "").strip().splitlines()[0].strip() if text else ""

def smart_title(text: str, fallback: str) -> str:
    t = first_line(text) or fallback
    return (t[:140] + "…") if len(t) > 140 else t

def smart_summary(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    s = text.strip()
    return (s[:1000] + "…") if len(s) > 1000 else s
