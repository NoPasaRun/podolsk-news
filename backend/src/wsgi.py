from contextlib import asynccontextmanager

from fastapi import FastAPI

from orm.db import init_db, close_db
from routes.auth import router as auth_router
from settings import settings

from fastapi.openapi.utils import get_openapi


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db(generate_schemas=False)
    try:
        yield
    finally:
        await close_db()


def custom_openapi():
    openapi_schema = get_openapi(
        title="News API",
        version="1.0.0",
        routes=app.routes,
        description="API docs",
    )
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    openapi_schema["security"] = [{"bearerAuth": []}]
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
