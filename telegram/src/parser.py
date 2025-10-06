import asyncio
from datetime import timezone

import asyncpg
from telethon import TelegramClient, errors

from db import fetch_active_telegram_sources, upsert_article
from settings import settings
from utils import normalize_handle, make_post_url, smart_title, smart_summary


async def crawl_once(pool: asyncpg.Pool, client: TelegramClient, fetch_limit: int, language: str):
    async with pool.acquire() as conn:
        sources = await fetch_active_telegram_sources(conn)
    if not sources:
        print("Нет активных telegram-источников")
        return

    for source_id, domain in sources:
        handle = normalize_handle(domain or "")
        if not handle:
            print("Источник id=%s: некорректный domain='%s'", source_id, domain)
            continue

        try:
            entity = await client.get_entity(handle)
        except errors.FloodWaitError as e:
            print("FloodWait %ss get_entity(%s)", e.seconds, handle)
            await asyncio.sleep(e.seconds + 1)
            continue
        except Exception as e:
            print("get_entity(%s) ошибка: %s", handle, e)
            continue

        processed = 0
        try:
            async for m in client.iter_messages(entity, limit=max(1, fetch_limit)):
                text = m.text or ""
                if not (text or m.media):
                    continue

                url = make_post_url(handle, m.id)
                title = smart_title(text, fallback=f"Post {m.id}")
                summary = smart_summary(text)
                published_at_utc = m.date
                if published_at_utc and published_at_utc.tzinfo is None:
                    published_at_utc = published_at_utc.replace(tzinfo=timezone.utc)

                try:
                    async with pool.acquire() as conn:
                        await upsert_article(
                            conn=conn,
                            source_id=source_id,
                            url=url,
                            title=title,
                            published_at_utc=published_at_utc,
                            summary=summary,
                            image=None,
                            language=language,
                        )
                        processed += 1
                except Exception as e:
                    print("upsert failed (%s/%s): %s", handle, m.id, e)
        except errors.FloodWaitError as e:
            print("FloodWait %ss iter_messages(%s)", e.seconds, handle)
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            print("iter_messages(%s) ошибка: %s", handle, e)

        print("Источник id=%s @%s: обработано %s", source_id, handle, processed)
        await asyncio.sleep(0.5)


async def crawler_loop(pool: asyncpg.Pool, client: TelegramClient):
    while True:
        try:
            await crawl_once(pool, client, settings.tg_fetch_limit, "russian")
        except Exception as e:
            print("Ошибка цикла краулера: %s", e)
        await asyncio.sleep(max(1, settings.crawl_interval_sec))
