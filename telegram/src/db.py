from datetime import datetime
from typing import Optional

import asyncpg

SQL_FETCH_ACTIVE_SOURCES = """
SELECT id, domain
FROM public.source
WHERE kind = 'telegram' AND status = 'active'
ORDER BY id;
"""

SQL_GET_SOURCE_BY_ID = """
SELECT id, kind, domain, status
FROM public.source
WHERE id = $1;
"""

SQL_UPDATE_SOURCE_STATUS = """
UPDATE public.source
SET status = $2, last_updated_at = NOW()
WHERE id = $1;
"""

UPSERT_SQL = """
SELECT *
FROM upsert_article_with_cluster($1, $2, $3, $4, $5, $6, $7);
"""


async def fetch_active_telegram_sources(conn: asyncpg.Connection):
    rows = await conn.fetch(SQL_FETCH_ACTIVE_SOURCES)
    return [(r["id"], r["domain"]) for r in rows]


async def get_source_by_id(conn: asyncpg.Connection, source_id: int):
    return await conn.fetchrow(SQL_GET_SOURCE_BY_ID, source_id)


async def update_source_status(conn: asyncpg.Connection, source_id: int, status: str):
    await conn.execute(SQL_UPDATE_SOURCE_STATUS, source_id, status)


async def upsert_article(conn: asyncpg.Connection,
                         source_id: int,
                         url: str,
                         title: str,
                         published_at_utc: datetime,
                         summary: Optional[str],
                         image: Optional[str],
                         language: str):
    return await conn.fetchrow(
        UPSERT_SQL, source_id, url, title, published_at_utc, summary, image, language
    )
