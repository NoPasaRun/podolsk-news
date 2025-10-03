from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2.2. Сгенерированная колонка tsvector
ALTER TABLE article
ADD COLUMN IF NOT EXISTS search_tsv tsvector
    GENERATED ALWAYS AS (
        to_tsvector('russian', coalesce(title,'') || ' ' || coalesce(summary,''))
    ) STORED;

-- 2.3. Индексы
CREATE INDEX IF NOT EXISTS article_title_trgm_idx   ON article USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS article_summary_trgm_idx ON article USING GIN (summary gin_trgm_ops);
CREATE INDEX IF NOT EXISTS article_search_tsv_idx   ON article USING GIN (search_tsv);

-- (опционально под скорость)
CREATE INDEX IF NOT EXISTS article_created_at_idx   ON article (created_at);
CREATE INDEX IF NOT EXISTS article_cluster_idx      ON article (cluster_id);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
DROP EXTENSION pg_trgm;

-- 2.2. Сгенерированная колонка tsvector
ALTER TABLE article DROP COLUMN IF EXISTS search_tsv;

-- 2.3. Индексы
DROP INDEX IF EXISTS article_title_trgm_idx;
DROP INDEX IF EXISTS article_summary_trgm_idx;
DROP INDEX IF EXISTS article_search_tsv_idx;

-- (опционально под скорость)
DROP INDEX IF EXISTS article_created_at_idx;
DROP INDEX IF EXISTS article_cluster_idx;"""

