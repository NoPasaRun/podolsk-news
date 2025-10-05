from fastapi import APIRouter, Depends
from orm.models import User
from utils.auth import get_current_user


router = APIRouter()


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "phone": user.phone}