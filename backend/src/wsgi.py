from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orm.db import init_db, close_db
from routes.auth import router as auth_router
from routes.news import router as news_router
from routes.user import router as user_router
from routes.source import router as source_router
from ws.source import source_ws
from settings import settings

from fastapi.openapi.utils import get_openapi
from redis.asyncio import Redis, ConnectionPool

from utils.redis import RedisBroker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(generate_schemas=False)
    pool = ConnectionPool.from_url(
        settings.redis.url,
        decode_responses=True, 
        max_connections=40
    )
    app.state.redis = Redis(connection_pool=pool)
    app.state.broker = RedisBroker(
        url=settings.redis.url,
        in_channel=settings.redis.in_channel,
        out_channel=settings.redis.out_channel,
    )
    await app.state.broker.start()
    try:
        yield
    finally:
        await close_db()
        await app.state.redis.close()
        await app.state.broker.stop()


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app.url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.openapi = custom_openapi
app.include_router(auth_router)
app.include_router(news_router)
app.include_router(user_router)
app.include_router(source_router)
app.add_websocket_route("/ws", source_ws)
