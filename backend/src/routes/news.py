from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime

from tortoise.expressions import Q
from tortoise.functions import Max

from orm.models import Topic, User, Article, UserArticleState, Cluster
from schemes.base import CursorPage, ToggleRequest
from schemes.news import TopicOut
from utils.auth import get_current_user, get_optional_user
from utils.cursor import parse_cursor, make_cursor
from utils.enums import Language

router = APIRouter(prefix="/news", tags=["news"])


async def update_user_article_state(user: User, article_id: int, **kwargs) -> bool:
    art = await Article.get_or_none(id=article_id)
    if not art:
        raise HTTPException(404, "Not found")
    cluster = await art.cluster
    rec, _ = await UserArticleState.get_or_create(
        user_id=user.id, cluster=cluster
    )
    for key, value in kwargs.items():
        setattr(rec, key, value)
    return not await rec.save()



@router.get("/topics/all", response_model=List[TopicOut])
async def list_topics():
    rows = await Topic.all().order_by("id")
    return [TopicOut(id=r.id, code=r.code, title=r.title) for r in rows]


@router.post("/{article_id}/read")
async def toggle_read(article_id: int, body: ToggleRequest, user: User = Depends(get_current_user)):
    return {"ok": await update_user_article_state(user, article_id, read=bool(body.value))}


@router.post("/{article_id}/bookmark")
async def toggle_bookmark(article_id: int, body: ToggleRequest, user: User = Depends(get_current_user)):
    return {"ok": await update_user_article_state(user, article_id, bookmarked=bool(body.value))}


@router.get("/all", response_model=CursorPage)
async def list_articles_grouped(
    user: User = Depends(get_optional_user),

    # фильтры
    topic_ids: Optional[List[int]] = Query(None),
    source_ids: Optional[List[int]] = Query(None),  # пересекаем с подключёнными
    language: Optional[Language] = Query(None),
    q: Optional[str] = Query(None, min_length=2),
    since: Optional[str] = Query(None),  # ISO
    until: Optional[str] = Query(None),

    # выборки внутри кластера
    max_articles_per_cluster: int = Query(6, ge=1, le=20),
    order_in_cluster: Literal["date_desc", "date_asc"] = "date_desc",

    # сортировка/пагинация кластеров
    sort: Literal["recent", "weight"] = "recent",
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = None,
):
    # --- разрешённые источники пользователя
    allowed = set()
    if user is not None:
        my_src = set(await user.source_ids())
        if source_ids:
            allowed = my_src.intersection(set(source_ids))
        else:
            allowed = my_src
    if not allowed:
        return {"items": [], "next_cursor": None}

    # ===== 1) Выбираем кластеры, где есть статьи из allowed и проходят фильтры
    cqs = Cluster.filter(articles__source_id__in=list(allowed)).distinct()

    if topic_ids:
        cqs = cqs.filter(cluster_topics__topic_id__in=topic_ids)
    if language:
        cqs = cqs.filter(language=language)
    if since:
        cqs = cqs.filter(first_published_at__gte=datetime.fromisoformat(since))
    if until:
        cqs = cqs.filter(first_published_at__lte=datetime.fromisoformat(until))
    if q:
        cqs = cqs.filter(Q(title__icontains=q) | Q(summary__icontains=q))

    # аннотируем "последнюю публикацию" по моим источникам — для сортировки/курсора
    cqs = cqs.annotate(last_pub=Max("articles__published_at"))

    if sort == "weight":
        cqs = cqs.order_by("-weight", "-last_pub", "-id")
    else:  # recent
        cqs = cqs.order_by("-last_pub", "-id")

    if cursor:
        cdt, cid = parse_cursor(cursor)
        if sort == "weight":
            # упрощённо: пагиним по last_pub + id
            cqs = cqs.filter(Q(last_pub__lt=cdt) | Q(last_pub=cdt, id__lt=cid))
        else:
            cqs = cqs.filter(Q(last_pub__lt=cdt) | Q(last_pub=cdt, id__lt=cid))

    clusters = await cqs.limit(limit)
    if not clusters:
        return {"items": [], "next_cursor": None}

    cluster_ids = [c.id for c in clusters]

    # ===== 2) Внутренняя выборка статей этих кластеров (только мои источники)
    aqs = Article.filter(cluster_id__in=cluster_ids, source_id__in=list(allowed)).prefetch_related("source")

    if language:
        aqs = aqs.filter(language=language)
    if since:
        aqs = aqs.filter(published_at__gte=datetime.fromisoformat(since))
    if until:
        aqs = aqs.filter(published_at__lte=datetime.fromisoformat(until))

    if order_in_cluster == "date_asc":
        aqs = aqs.order_by("cluster_id", "published_at", "id")
    else:
        aqs = aqs.order_by("cluster_id", "-published_at", "-id")

    arts = await aqs

    # ===== 3) Группируем в память и обрезаем до max_articles_per_cluster
    grouped: dict[int, list] = {cid: [] for cid in cluster_ids}
    for a in arts:
        lst = grouped.setdefault(a.cluster_id, [])
        if len(lst) < max_articles_per_cluster:
            lst.append({
                "id": a.id,
                "source_id": a.source_id,
                "source_domain": a.source.domain,
                "url": a.url,
                "title": a.title,
                "summary": a.summary,
                "published_at": a.published_at.isoformat(),
                "language": a.language,
            })

    # Собираем ответ строго в нужном формате
    items = [{"cluster_id": cid, "articles": grouped.get(cid, [])} for cid in cluster_ids]

    # курсор по последнему кластеру на странице
    last = clusters[-1]
    next_cursor = make_cursor(getattr(last, "last_pub") or last.first_published_at, last.id)

    return {"items": items, "next_cursor": next_cursor}


