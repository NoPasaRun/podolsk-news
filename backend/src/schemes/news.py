from typing import List, Optional
from pydantic import BaseModel


class TopicOut(BaseModel):
    id: int
    title: str


class ArticleOut(BaseModel):
    id: int
    title: str
    url: str
    source_id: int
    source_name: str
    published_at: Optional[str]


class ClusterItem(BaseModel):
    cluster_id: int
    article: ArticleOut
    other_articles: List[ArticleOut] = []
    is_bookmarked: bool = False
    is_read: bool = False


class NewsListResponse(BaseModel):
    items: List[ClusterItem]
    next_cursor: Optional[str] = None
