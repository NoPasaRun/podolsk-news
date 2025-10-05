from contextlib import asynccontextmanager

from fastapi import FastAPI

from orm.db import init_db, close_db
from routes.auth import router as auth_router
from routes.news import router as news_router
from routes.user import router as user_router
from routes.source import router as source_router
from settings import settings

from fastapi.openapi.utils import get_openapi
from redis.asyncio import Redis, ConnectionPool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(generate_schemas=False)
    pool = ConnectionPool.from_url(
        f"redis://redis:6379", 
        decode_responses=True, 
        max_connections=40
    )
    app.state.redis = Redis(connection_pool=pool)
    try:
        yield
    finally:
        await close_db()
        await app.state.redis.close()


def custom_openapi():
    openapi_schema = get_openapi(
        title="News API",
        version="1.0.0",
        routes=app.routes,
        description="API docs",
    )
    openapi_schema["servers"] = [{"url": "/api"}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(
    title="News API",
    root_path="/api",
    lifespan=lifespan,
    **(
        {
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json"
        }
        if settings.app.debug else {}
    )
)
app.openapi = custom_openapi
app.include_router(auth_router)
app.include_router(news_router)
app.include_router(user_router)
app.include_router(source_router)
