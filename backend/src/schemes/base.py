from typing import Optional

from pydantic import BaseModel


class ToggleRequest(BaseModel):
    value: bool


class CursorPage(BaseModel):
    items: list
    next_cursor: Optional[str] = None
