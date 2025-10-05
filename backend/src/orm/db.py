from tortoise import Tortoise
from settings import settings


TORTOISE_ORM = {
    "connections": {"default": settings.db.url},
    "apps": {
        "models": {
            "models": ["orm.models", "aerich.models"],
            "default_connection": "default",
        }
    },
}

async def init_db(generate_schemas: bool = True) -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    if generate_schemas:
        await Tortoise.generate_schemas()

async def close_db() -> None:
    await Tortoise.close_connections()