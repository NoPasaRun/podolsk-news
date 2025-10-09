from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, Query
from datetime import datetime

from tortoise.functions import Max

from orm.models import Topic, User, UserArticleState, Cluster
from schemes.base import CursorPage, ToggleRequest
from schemes.news import TopicOut
from utils.auth import get_current_user, get_optional_user
from utils.cursor import make_cursor_weight, make_cursor_recent
from utils.enums import Language
from utils.news import fetch_articles_for_clusters, fetch_cluster_flags, fetch_user_source_ranks, pick_primary, \
    apply_cluster_filters, resolve_allowed_source_ids, apply_keyset_cursor

router = APIRouter(prefix="/news", tags=["news"])


async def update_user_cluster_state(user: User, cluster_id: int, **kwargs) -> bool:
    exists = await Cluster.filter(id=cluster_id).exists()
    if not exists:
        return False
    rec, _ = await UserArticleState.get_or_create(
        user_id=user.id, cluster_id=cluster_id
    )
    for key, value in kwargs.items():
        setattr(rec, key, value)
    return not await rec.save()



@router.get("/topics/all", response_model=List[TopicOut])
async def list_topics():
    rows = await Topic.all().order_by("id")
    return [TopicOut(id=r.id, title=r.title) for r in rows]


@router.post("/{cluster_id}/read")
async def toggle_read(cluster_id: int, body: ToggleRequest, user: User = Depends(get_current_user)):
    return {"ok": await update_user_cluster_state(user, cluster_id, read=bool(body.value))}


@router.post("/{cluster_id}/bookmark")
async def toggle_bookmark(cluster_id: int, body: ToggleRequest, user: User = Depends(get_current_user)):
    return {"ok": await update_user_cluster_state(user, cluster_id, bookmarked=bool(body.value))}



@router.get("/all", response_model=CursorPage)
async def list_articles_grouped(
    user: User = Depends(get_optional_user),

    # фильтры
    topic_ids: Optional[List[int]] = Query(None),
    language: Optional[Language] = Query(None),
    q: Optional[str] = Query(None, min_length=2),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),

    # выборка внутри кластера
    max_articles_per_cluster: int = Query(6, ge=1, le=11),
    order_in_cluster: Literal["date_desc", "date_asc"] = "date_desc",
    bookmarkOnly: bool = Query(False),

    # сортировка/пагинация кластеров
    sort: Literal["recent", "weight"] = "recent",
    limit: int = Query(5, ge=1, le=21),
    cursor: Optional[str] = None,
):
    # 0) Разрешённые источники
    allowed = await resolve_allowed_source_ids(user)
    if not allowed:
        return {"items": [], "next_cursor": None}

    # 1) Базовый запрос по кластерам + фильтры
    cqs = Cluster.filter(articles__source_id__in=allowed).distinct()
    cqs = apply_cluster_filters(
        cqs,
        topic_ids=topic_ids,
        language=language,
        q=q,
        bookmarkOnly=bookmarkOnly,
        user=user
    )

    # 1.1) Аннотация "последней публикации" по моим источникам
    cqs = cqs.annotate(last_pub=Max("articles__published_at"))

    # 1.2) Сортировка
    if sort == "weight":
        order_by = ("-weight", "-last_pub", "-id")
    else:
        order_by = ("-last_pub", "-id")
    if q:
        order_by = ("-best_rank",) + order_by
    cqs = cqs.order_by(*order_by)

    # 1.3) Курсор (keyset) — корректный для конкретной сортировки
    cqs = apply_keyset_cursor(cqs, sort=sort, cursor=cursor)
    clusters = await cqs.limit(limit)

    if not clusters:
        return {"items": [], "next_cursor": None}

    cluster_ids = [c.id for c in clusters]

    # 2) Внутренние статьи кластеров (только из allowed)
    grouped = await fetch_articles_for_clusters(
        cluster_ids=cluster_ids,
        allowed_source_ids=allowed,
        since=since,
        until=until,
        order_in_cluster=order_in_cluster,
        max_articles_per_cluster=max_articles_per_cluster
    )

    # 3) Кластерные флаги (bookmarked/read) и ранги источников
    cluster_flags = await fetch_cluster_flags(user, cluster_ids)
    ranks = await fetch_user_source_ranks(user, allowed)

    # 4) Сборка ответа (article + other_articles + флаги)
    items = []
    for cid in cluster_ids:
        lst = grouped.get(cid, [])
        if not lst:
            continue
        primary = pick_primary(lst, ranks)
        others = [it for it in lst if it["id"] != primary["id"]]
        flags = cluster_flags.get(cid, {})
        items.append({
            "cluster_id": cid,
            "article": primary,
            "other_articles": others,
            "bookmarked": bool(flags.get("bookmarked", False)),
            "read": bool(flags.get("read", False)),
        })

    # 5) next_cursor — по последнему кластеру

    last = clusters[-1]
    last_pub = getattr(last, "last_pub") or getattr(last, "first_published_at")

    if sort == "weight":
        next_cursor = make_cursor_weight(getattr(last, "weight") or 0, last_pub, last.id)
    else:
        next_cursor = make_cursor_recent(last_pub, last.id)

    return {"items": items, "next_cursor": next_cursor}