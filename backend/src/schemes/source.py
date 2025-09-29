from typing import Optional, List

from pydantic import BaseModel

from utils.enums import SourceKind, SourceStatus


class SourceCreate(BaseModel):
    kind: SourceKind
    domain: str


class SourceOut(BaseModel):
    id: int
    kind: SourceKind
    domain: str
    status: SourceStatus
    created_at: str


class UserSourceOut(BaseModel):
    id: int
    source: SourceOut
    poll_interval_sec: int
    rank: int
    labels: List[str]
    created_at: str


class UserSourceUpdate(BaseModel):
    poll_interval_sec: Optional[int] = None
    rank: Optional[int] = None
    labels: Optional[List[str]] = None


class SourceCatalogItem(BaseModel):
    id: int
    kind: SourceKind
    domain: str
    status: SourceStatus
    parser_profile: Optional[str] = None
    created_at: str
    connected: bool              # есть ли UserSource у текущего юзера
    user_source_id: Optional[int] = None
