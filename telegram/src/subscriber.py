import asyncio
import json

from redis.asyncio import Redis
from typing import Tuple, Optional

import asyncpg

from db import update_source_status, get_source_by_id
from settings import settings

from telethon import TelegramClient, errors

from utils import normalize_handle


async def verify_source(pool: asyncpg.Pool, client: TelegramClient, source_id: int) -> Tuple[str, Optional[str]]:
    """
    Возвращает (status, error_message). status: 'active' или 'error'.
    Обновляет статус источника в БД:
      - при постоянной ошибке -> 'error'
      - при успехе -> 'active'
      - при временной ошибке -> БД не трогаем
    """
    async with pool.acquire() as conn:
        src = await get_source_by_id(conn, source_id)
        if not src:
            return "error", "source_not_found"
        if src["kind"] != "telegram":
            try:
                await update_source_status(conn, source_id, "error")
            except Exception:
                pass
            return "error", "kind_mismatch_not_telegram"

        handle = normalize_handle(src["domain"] or "")
        if not handle:
            try:
                await update_source_status(conn, source_id, "error")
            except Exception:
                pass
            return "error", "invalid_domain"

    # Проверяем через Telethon
    try:
        await client.get_entity(handle)
        # успех: активируем
        async with pool.acquire() as conn:
            try:
                await update_source_status(conn, source_id, "active")
            except Exception:
                pass
        return "active", None
    except errors.FloodWaitError as e:
        # временная ошибка — статус в БД не трогаем
        return "error", f"flood_wait_{e.seconds}s"
    except Exception as e:
        # постоянная — пометим error в БД
        async with pool.acquire() as conn:
            try:
                await update_source_status(conn, source_id, "error")
            except Exception:
                pass
        return "error", f"{type(e).__name__}: {e}"


async def redis_listener(pool: asyncpg.Pool, redis: Redis, client: TelegramClient):
    pubsub = redis.pubsub()
    await pubsub.subscribe(settings.redis_in_channel)
    print("Подписан на Redis: %s", settings.redis_in_channel)

    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not msg:
                await asyncio.sleep(0.1)
                continue

            raw = msg.get("data")
            try:
                payload = json.loads(raw)
            except Exception:
                # если прилетела строка "123:456" — поддержим и такой формат
                try:
                    s_id, u_id = str(raw).split(":", 1)
                    payload = {"source_id": int(s_id), "user_id": int(u_id)}
                except Exception:
                    payload = {}

            source_id = payload.get("source_id")
            user_id = payload.get("user_id")

            if not isinstance(source_id, int) or not isinstance(user_id, int):
                out = {"source_id": source_id, "user_id": user_id, "status": "error", "error": "bad_payload"}
                await redis.publish(settings.redis_out_channel, json.dumps(out, ensure_ascii=False))
                continue

            status, err = await verify_source(pool, client, source_id)
            out = {"source_id": source_id, "user_id": user_id, "status": status, "error": err}
            await redis.publish(settings.redis_out_channel, json.dumps(out, ensure_ascii=False))
    finally:
        await pubsub.unsubscribe(settings.redis_in_channel)
        await pubsub.close()
