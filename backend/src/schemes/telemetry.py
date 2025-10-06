from typing import Literal, Optional, List
from pydantic import BaseModel, Field

EventType = Literal["impression", "dwell", "click", "outbound"]

class Event(BaseModel):
    session_id: str
    ts: int
    type: EventType
    cluster_id: int
    article_id: Optional[int] = None
    source_id: Optional[int] = None
    position: Optional[int] = None
    dwell_ms: Optional[int] = None
    url: Optional[str] = None

class EventBatch(BaseModel):
    events: List[Event] = Field(default_factory=list)
