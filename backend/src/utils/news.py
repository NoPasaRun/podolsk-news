from datetime import datetime, timezone
import random
from typing import Optional, List, Literal, Dict

from tortoise.expressions import Q, RawSQL
from tortoise.fields import BooleanField, FloatField

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
):
    if topic_ids:
        qs = qs.filter(cluster_topics__topic_id__in=topic_ids)
    if language:
        qs = qs.filter(language=language)
    if q:
        q_lit = q.replace("'", "''")
        tsq = (
            "(SELECT ("
            "  CASE WHEN cardinality(arr)=0 THEN '' "
            "       WHEN cardinality(arr)=1 THEN arr[1] || ':*' "
            "       ELSE array_to_string(arr[1:cardinality(arr)-1] || (arr[cardinality(arr)] || ':*'), ' & ') "
            "  END"
            ")::tsquery "
            f" FROM (SELECT regexp_split_to_array(plainto_tsquery('{language}'::regconfig, '{q_lit}')::text, ' & ') AS arr) _)"
        )
        best_rank_sql = (
            "COALESCE(("
            '  SELECT MAX(ts_rank_cd(a.search_tsv, ' + tsq + '))'
            '  FROM "article" a'
            '  WHERE a.cluster_id = "cluster".id'
            '    AND a.search_tsv @@ ' + tsq +
            "), 0.0)"
        )

        qs = qs.annotate(
            best_rank=RawSQL(best_rank_sql)
        ).filter(best_rank__gt=0)
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
    since: Optional[datetime],
    until: Optional[datetime],
    order_in_cluster: Literal["date_desc", "date_asc"],
    max_articles_per_cluster: int,
) -> Dict[int, List[dict]]:
    qs = Article.filter(cluster_id__in=cluster_ids, source_id__in=allowed_source_ids).prefetch_related("source")
    if since:
        qs = qs.filter(published_at__gte=since)
    if until:
        qs = qs.filter(published_at__lte=until)

    order_by = tuple(val for condition, val in [
        (order_in_cluster == "date_asc", "published_at"),
        (order_in_cluster == "date_desc", "-published_at")
    ] if condition)

    arts = await qs.order_by(*order_by)

    grouped: Dict[int, List[dict]] = {cid: [] for cid in cluster_ids}
    for a in arts:
        payload = {
            "id": a.id,
            "source_id": a.source_id,
            "source_domain": a.source.domain if getattr(a, "source", None) else None,
            "url": a.url,
            "title": a.title,
            "summary": a.summary,
            "published_at": a.published_at.isoformat() if a.published_at else None
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


def pick_primary(articles: List[dict], ranks: Dict[int, int], sort_by: Literal['recent', 'weight'] = 'weight') -> dict:
    if not articles:
        return {}
    if ranks and sort_by == 'weight':
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
    else:
        candidates = articles
    return max(candidates, key=lambda x: (_parse_dt_safe(x["published_at"]), x["id"]))
