from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from orm.models import User, Source, UserSource
from schemes.base import CursorPage
from schemes.source import UserSourceOut, SourceCreate, SourceOut, UserSourceUpdate, SourceCatalogItem
from utils.auth import get_current_user, get_optional_user
from utils.cursor import parse_cursor, make_cursor
from utils.enums import SourceKind, SourceStatus

router = APIRouter(prefix="/source", tags=["source"])


async def build_user_source_out(us: UserSource) -> UserSourceOut:
    src = await us.source
    return UserSourceOut(
        id=us.id,
        source=SourceOut(
            id=src.id, kind=src.kind, domain=src.domain, status=src.status,
            parser_profile=src.parser_profile, created_at=src.created_at.isoformat()
        ),
        poll_interval_sec=us.poll_interval_sec,
        rank=us.rank,
        labels=us.labels or [],
        created_at=us.created_at.isoformat()
    )


@router.post("/create", response_model=UserSourceOut)
async def create_source(payload: SourceCreate, user: User = Depends(get_current_user)):
    """
    Создаёт Source (если такого (kind,domain) нет) и тут же подключает его пользователю (UserSource).
    Редактировать/удалять Source нельзя — только свой UserSource.
    """
    async with in_transaction():
        src, _ = await Source.get_or_create(
            kind=payload.kind, domain=payload.domain,
            defaults={
                "status": "validating",
                "parser_profile": payload.parser_profile,
                "parse_overrides": payload.parse_overrides
            }
        )
        us, _ = await UserSource.get_or_create(user_id=user.id, source_id=src.id)
    # возврат
    return await build_user_source_out(us)


@router.post("/add", response_model=UserSourceOut)
async def add_user_source(source_id: int, user: User = Depends(get_current_user)):
    if not (source := await Source.get_or_none(id=source_id)):
        raise HTTPException(404, "Not found")
    us, created = await UserSource.get_or_create(user=user, source=source)
    return await build_user_source_out(us)


@router.delete("/remove")
async def remove_user_source(user_source_id: int, user: User = Depends(get_current_user)):
    us = await UserSource.get_or_none(id=user_source_id, user_id=user.id)
    if not us:
        raise HTTPException(404, "Not found")
    await us.delete()
    return {"ok": True}


@router.get("/my", response_model=CursorPage)
async def list_my_sources(
    user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None
):
    qs = UserSource.filter(user_id=user.id).prefetch_related("source").order_by("id")
    if cursor:
        _, last_id = parse_cursor(cursor)
        qs = qs.filter(id__gt=last_id)

    rows = await qs.limit(limit)
    items = []
    for us in rows:
        src = us.source
        items.append(UserSourceOut(
            id=us.id,
            source=SourceOut(
                id=src.id, kind=src.kind, domain=src.domain, status=src.status,
                parser_profile=src.parser_profile, created_at=src.created_at.isoformat()
            ),
            poll_interval_sec=us.poll_interval_sec,
            rank=us.rank,
            labels=us.labels or [],
            created_at=us.created_at.isoformat(),
        ))
    next_cursor = make_cursor(datetime.now(timezone.utc), rows[-1].id) if rows else None
    return {"items": items, "next_cursor": next_cursor}


@router.get("/all", response_model=CursorPage)
async def catalog_sources(
    user: Optional[User] = Depends(get_optional_user),
    kind: Optional[SourceKind] = Query(None),
    status: Optional[SourceStatus] = Query(None),
    q: Optional[str] = Query(None, min_length=2),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None
):
    qs = Source.all().order_by("id")

    if kind:
        qs = qs.filter(kind=kind)
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(domain__icontains=q))

    if cursor:
        _, last_id = parse_cursor(cursor)
        qs = qs.filter(id__gt=last_id)

    rows = await qs.limit(limit)
    # подтянем одним запросом user-линки
    connected_map = {}
    if user:
        links = await UserSource.filter(user_id=user.id, source_id__in=[r.id for r in rows]).values("id","source_id")
        connected_map = {l["source_id"]: l["id"] for l in links}

    items = [
        SourceCatalogItem(
            id=r.id, kind=r.kind, domain=r.domain, status=r.status,
            parser_profile=r.parser_profile, created_at=r.created_at.isoformat(),
            connected=(r.id in connected_map),
            user_source_id=connected_map.get(r.id)
        )
        for r in rows
    ]
    next_cursor = make_cursor(datetime.now(timezone.utc), rows[-1].id) if rows else None
    return {"items": items, "next_cursor": next_cursor}


@router.patch("/update/{user_source_id}", response_model=UserSourceOut)
async def update_source(user_source_id: int, body: UserSourceUpdate, user: User = Depends(get_current_user)):
    us = await UserSource.get_or_none(id=user_source_id, user_id=user.id).prefetch_related("source")
    if not us:
        raise HTTPException(404, "Not found")
    patch = body.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(us, k, v)
    await us.save()
    src = us.source
    return UserSourceOut(
        id=us.id,
        source=SourceOut(
            id=src.id, kind=src.kind, domain=src.domain, status=src.status,
            parser_profile=src.parser_profile, created_at=src.created_at.isoformat()
        ),
        poll_interval_sec=us.poll_interval_sec,
        rank=us.rank,
        labels=us.labels or [],
        created_at=us.created_at.isoformat(),
    )