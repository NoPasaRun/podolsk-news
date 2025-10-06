import asyncio

import asyncpg
from redis.asyncio import Redis

from parser import crawler_loop
from subscriber import redis_listener
from settings import settings

from telethon import TelegramClient


async def main():
    try:
        import uvloop  # type: ignore
        uvloop.install()
    except Exception:
        pass

    pool = await asyncpg.create_pool(dsn=settings.db_url, min_size=1, max_size=5)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    client = TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Telethon-сессия не авторизована. Авторизуй файл сессии отдельно.")

    print("Запускаю listener и crawler…")
    try:
        await asyncio.gather(
            redis_listener(pool, redis, client),
            crawler_loop(pool, client),
        )
    finally:
        await client.disconnect()
        await redis.close()
        await pool.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановлено пользователем")