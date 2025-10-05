from typing import List

from pydantic import BaseModel


class User(BaseModel):
    id: int
    email: str | None
    name: str | None
    avatar: str | None


class UserPrefsUpdate(BaseModel):
    topic_ids: List[int] = []
    source_ids: List[int] = []
