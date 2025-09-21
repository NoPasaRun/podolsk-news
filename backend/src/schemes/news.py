from typing import List, Optional
from pydantic import BaseModel, AnyUrl
from utils.enums import Language, TopicKind


class TopicOut(BaseModel):
    id: int
    code: TopicKind
    title: str


class ClusterBasic(BaseModel):
    id: int
    title: str
    summary: str | None = None
    first_published_at: str
    last_updated_at: str
    weight: int


class ArticleBasic(BaseModel):
    id: int
    source_id: int
    source_domain: str
    url: str
    title: str
    summary: str | None = None
    published_at: str


class ClusterArticlesOut(BaseModel):
    cluster: ClusterBasic
    articles: List[ArticleBasic]
