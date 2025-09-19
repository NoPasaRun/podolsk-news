from fastapi import APIRouter
from datetime import datetime
from random import randint


router = APIRouter(prefix="/news", tags=["news"])


@router.get("/list")
async def get_news():
    return [{
        "title": f"Title_{i}",
        "description": "Lorem ipsum dolor sit amet consectetur adipisicing elit.",
        "created_at": datetime(year=2025, month=9, day=randint(1, 30), hour=randint(0, 23)),
        "author": f"Author_{i}",
        "link": "https://google.com"

    } for i in range(1, 11)]
