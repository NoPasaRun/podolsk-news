from datetime import datetime, timezone
import random
from typing import Optional, List, Literal, Dict

from tortoise.expressions import Q

from orm.models import Source, User, Article, UserArticleState, UserSource
from utils.cursor import parse_cursor_weight, parse_cursor_recent, _from_micros
from utils.enums import Language


async def resolve_allowed_source_ids(user: Optional[User]) -> List[int]:
    if user is not None:
        return list(await user.source_ids())
    rows = await Source.filter(is_default=True).values_list("id", flat=True)
    return list(rows)


def apply_cluster_filters(
    qs, *,
    topic_ids: Optional[List[str]],
    language: Optional[Language],
    q: Optional[str],
    since: Optional[datetime],
    until: Optional[datetime],
):
    if topic_ids:
        qs = qs.filter(cluster_topics__topic_id__in=topic_ids)
    if language:
        qs = qs.filter(language=language)
    if since:
        qs = qs.filter(first_published_at__gte=since)
    if until:
        qs = qs.filter(first_published_at__lte=until)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q))
    return qs

def apply_keyset_cursor(qs, *, sort: Literal["recent", "weight"], cursor: Optional[str]):
    if not cursor:
        return qs
    if sort == "weight":
        w, us, cid = parse_cursor_weight(cursor)
        cdt = _from_micros(us)
        return qs.filter(
            Q(weight__lt=w) |
            (Q(weight=w) & (Q(last_pub__lt=cdt) | Q(last_pub=cdt, id__lt=cid)))
        )
    us, cid = parse_cursor_recent(cursor)
    cdt = _from_micros(us)
    return qs.filter(
        Q(last_pub__lt=cdt) |
        Q(last_pub=cdt, id__lt=cid)
    )


async def fetch_articles_for_clusters(
    cluster_ids: List[int],
    allowed_source_ids: List[int],
    *,
    language: Optional[Language],
    since: Optional[datetime],
    until: Optional[datetime],
    order_in_cluster: Literal["date_desc", "date_asc"],
    max_articles_per_cluster: int,
) -> Dict[int, List[dict]]:
    qs = Article.filter(cluster_id__in=cluster_ids, source_id__in=allowed_source_ids).prefetch_related("source")
    if language:
        qs = qs.filter(language=language)
    if since:
        qs = qs.filter(published_at__gte=since)
    if until:
        qs = qs.filter(published_at__lte=until)

    if order_in_cluster == "date_asc":
        qs = qs.order_by("cluster_id", "published_at", "id")
    else:
        qs = qs.order_by("cluster_id", "-published_at", "-id")

    arts = await qs

    grouped: Dict[int, List[dict]] = {cid: [] for cid in cluster_ids}
    for a in arts:
        payload = {
            "id": a.id,
            "source_id": a.source_id,
            "source_domain": a.source.domain if getattr(a, "source", None) else None,
            "url": a.url,
            "title": a.title,
            "summary": a.summary,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "language": a.language,
        }
        lst = grouped.setdefault(a.cluster_id, [])
        if len(lst) < max_articles_per_cluster:
            lst.append(payload)

    return grouped


async def fetch_cluster_flags(user: Optional[User], cluster_ids: List[int]) -> Dict[int, dict]:
    """
    Возвращает cluster_id -> {bookmarked, read} для текущего пользователя.
    """
    if user is None or not cluster_ids:
        return {}
    rows = await UserArticleState.filter(
        user_id=user.id, cluster_id__in=cluster_ids
    ).values("cluster_id", "bookmarked", "read")
    return {r["cluster_id"]: {"bookmarked": r["bookmarked"], "read": r["read"]} for r in rows}


async def fetch_user_source_ranks(user: Optional[User], allowed_source_ids: List[int]) -> Dict[int, int]:
    if user is None:
        return {}
    rows = await UserSource.filter(
        user_id=user.id,
        source_id__in=allowed_source_ids
    ).values("source_id", "rank")
    return {r["source_id"]: r["rank"] for r in rows}


def _parse_dt_safe(iso: Optional[str]) -> datetime:
    if not iso:
        return datetime.min.replace(tzinfo=timezone.utc)
    s = iso
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def pick_primary(articles: List[dict], ranks: Dict[int, int]) -> dict:
    if not articles:
        return {}
    if ranks:
        best_rank = None
        candidates: List[dict] = []
        for it in articles:
            r = ranks.get(it["source_id"])
            if r is None:
                continue
            if best_rank is None or r > best_rank:
                best_rank = r
                candidates = [it]
            elif r == best_rank:
                candidates.append(it)
        if candidates:
            return max(candidates, key=lambda x: (_parse_dt_safe(x["published_at"]), x["id"]))
    return random.choice(articles)
