import random
from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, timezone

from tortoise.expressions import Q
from tortoise.functions import Max

from orm.models import Topic, User, Article, UserArticleState, Cluster, UserSource, Source
from schemes.base import CursorPage, ToggleRequest
from schemes.news import TopicOut
from utils.auth import get_current_user, get_optional_user
from utils.cursor import parse_cursor, make_cursor
from utils.enums import Language

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
    return [TopicOut(id=r.id, code=r.code, title=r.title) for r in rows]


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
    since: Optional[str] = Query(None),  # ISO
    until: Optional[str] = Query(None),

    # выборки внутри кластера
    max_articles_per_cluster: int = Query(6, ge=1, le=20),
    order_in_cluster: Literal["date_desc", "date_asc"] = "date_desc",

    # сортировка/пагинация кластеров
    sort: Literal["recent", "weight"] = "recent",
    limit: int = Query(5, ge=1, le=100),
    cursor: Optional[str] = None,
):
    # --- разрешённые источники пользователя
    allowed = set(
        await user.source_ids()
        if user is not None
        else [
            row.get("id") for row in
            await Source.filter(is_default=True).values("id")
        ]
    )

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

    cluster_status = {}
    if user is not None and cluster_ids:
        rows = await UserArticleState.filter(
            user_id=user.id, cluster_id__in=cluster_ids
        ).values("cluster_id", "bookmarked", "read")
        cluster_status = {r["cluster_id"]: {"bookmarked": r["bookmarked"], "read": r["read"]} for r in rows}

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

    ranks: dict[int, int] = {}
    if user is not None:
        rows = await UserSource.filter(
            user_id=user.id,
            # если allowed не None, смысла тянуть лишние нет
            **({"source_id__in": list(allowed)} if allowed is not None else {})
        ).values("source_id", "rank")
        ranks = {r["source_id"]: r["rank"] for r in rows}

    def _parse_dt(s: Optional[str]) -> datetime:
        if not s:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            # поддержим 'Z'
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    def pick_primary(lst: list[dict]) -> dict:
        # если есть ранги — берём из источника с максимальным rank,
        # при равенстве ранга — самую свежую по published_at
        if ranks:
            best_rank = None
            candidates: list[dict] = []
            for it in lst:
                r = ranks.get(it["source_id"])
                if r is None:
                    continue
                if best_rank is None or r > best_rank:
                    best_rank = r
                    candidates = [it]
                elif r == best_rank:
                    candidates.append(it)
            if candidates:
                return max(candidates, key=lambda x: (_parse_dt(x["published_at"]), x["id"]))
        # аноним/нет рангов — случайная статья
        return random.choice(lst)

    # Собираем ответ в новом формате: article + other_articles
    items = []
    for cid in cluster_ids:
        lst = grouped.get(cid, [])
        if not lst:
            # пустые кластеры пропустим
            continue
        primary = pick_primary(lst)
        others = [it for it in lst if it["id"] != primary["id"]]
        items.append({
            "cluster_id": cid,
            "article": primary,
            "other_articles": others,
            "bookmarked": cluster_status.get(cid, {}).get("bookmarked", False),
            "read": cluster_status.get(cid, {}).get("read", False),
        })

    # курсор по последнему кластеру на странице (как было)
    last = clusters[-1]
    next_cursor = make_cursor(getattr(last, "last_pub") or last.first_published_at, last.id)

    return {"items": items, "next_cursor": next_cursor}
