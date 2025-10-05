from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException, Request

from tortoise.transactions import in_transaction

from orm.models import User, Source, UserSource
from schemes.source import UserSourceOut, SourceCreate, SourceOut, UserSourceUpdate, SourceCatalogItem
from utils.auth import get_current_user, get_optional_user
from utils.enums import SourceKind, SourceStatus
from utils.redis import RedisBroker

router = APIRouter(prefix="/source", tags=["source"])


def get_broker(request: Request) -> RedisBroker:
    return request.app.state.broker


async def build_user_source_out(us: UserSource) -> UserSourceOut:
    src = await us.source
    return UserSourceOut(
        id=us.id,
        source=SourceOut(
            id=src.id, kind=src.kind,
            domain=src.domain, status=src.status,
            created_at=src.created_at.isoformat()
        ),
        poll_interval_sec=us.poll_interval_sec,
        rank=us.rank,
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
            kind=payload.kind, domain=payload.domain
        )
        us, _ = await UserSource.get_or_create(user_id=user.id, source_id=src.id)
    # возврат
    return await build_user_source_out(us)


@router.post("/{source_id}", response_model=UserSourceOut)
async def add_user_source(source_id: int, user: User = Depends(get_current_user)):
    if not (source := await Source.get_or_none(id=source_id)):
        raise HTTPException(404, "Not found")
    us, created = await UserSource.get_or_create(user=user, source=source)
    return await build_user_source_out(us)


@router.delete("/{source_id}")
async def remove_user_source(source_id: int, user: User = Depends(get_current_user)):
    us = await UserSource.get_or_none(source_id=source_id, user_id=user.id)
    if not us:
        raise HTTPException(404, "Not found")
    await us.delete()
    return {"ok": True}


@router.get("/my")
async def list_my_sources(
    user: User = Depends(get_current_user)
) -> List[UserSourceOut]:
    qs = UserSource.filter(user_id=user.id).prefetch_related("source").order_by("id")
    return [await build_user_source_out(us) for us in await qs]


@router.get("/all")
async def catalog_sources(
    user: Optional[User] = Depends(get_optional_user),
    kind: Optional[SourceKind] = Query(None),
    status: Optional[SourceStatus] = Query(None)
) -> List[SourceCatalogItem]:
    qs = Source.filter(status=SourceStatus.ACTIVE).order_by("id")

    if kind:
        qs = qs.filter(kind=kind)
    if status:
        qs = qs.filter(status=status)
    rows = await qs

    connected_map = {}
    if user:
        links = await UserSource.filter(
            user_id=user.id,
            source_id__in=[r.id for r in rows]
        ).values("id","source_id")
        connected_map = {l["source_id"]: l["id"] for l in links}

    return [
        SourceCatalogItem(
            id=r.id, kind=r.kind, domain=r.domain, status=r.status,
            created_at=r.created_at.isoformat(),
            connected=(r.id in connected_map),
            user_source_id=connected_map.get(r.id)
        )
        for r in rows
    ]


@router.patch("/update/{user_source_id}", response_model=UserSourceOut)
async def update_source(user_source_id: int, body: UserSourceUpdate, user: User = Depends(get_current_user)):
    us = await UserSource.get_or_none(id=user_source_id, user_id=user.id).prefetch_related("source")
    if not us:
        raise HTTPException(404, "Not found")
    patch = body.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(us, k, v)
    await us.save()
    return await build_user_source_out(us)
