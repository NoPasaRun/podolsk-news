from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE topic DROP CONSTRAINT "topic_code_key";
        DROP INDEX "idx_cluster_weight_4e0093";
        DROP INDEX "idx_cluster_first_p_29810b";
        DROP INDEX "idx_cluster_last_up_8dcdbb";
        DROP INDEX "idx_article_source__1429e8";
        DROP INDEX "idx_article_cluster_300cfc";
        ALTER TABLE "article" ALTER COLUMN "language" TYPE VARCHAR(8) USING "language"::VARCHAR(8);
        ALTER TABLE "cluster" ALTER COLUMN "language" TYPE VARCHAR(8) USING "language"::VARCHAR(8);
        CREATE  INDEX "idx_article_cluster_300cfc" ON "article" ("cluster_id", "published_at");
        CREATE  INDEX "idx_article_source__1429e8" ON "article" ("source_id", "published_at");
        CREATE  INDEX "idx_cluster_last_up_8dcdbb" ON "cluster" ("last_updated_at");
        CREATE  INDEX "idx_cluster_weight_4e0093" ON "cluster" ("weight");
        CREATE  INDEX "idx_cluster_first_p_29810b" ON "cluster" ("first_published_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX "idx_cluster_first_p_29810b";
        DROP INDEX "idx_cluster_weight_4e0093";
        DROP INDEX "idx_cluster_last_up_8dcdbb";
        DROP INDEX "idx_article_source__1429e8";
        DROP INDEX "idx_article_cluster_300cfc";
        ALTER TABLE "article" ALTER COLUMN "language" TYPE VARCHAR(8) USING "language"::VARCHAR(8);
        ALTER TABLE "cluster" ALTER COLUMN "language" TYPE VARCHAR(8) USING "language"::VARCHAR(8);
        CREATE UNIQUE INDEX "topic_code_key" ON "topic" ("code");
        CREATE  INDEX "idx_article_cluster_300cfc" ON "article" ("cluster_id", "published_at");
        CREATE  INDEX "idx_article_source__1429e8" ON "article" ("source_id", "published_at");
        CREATE  INDEX "idx_cluster_last_up_8dcdbb" ON "cluster" ("last_updated_at");
        CREATE  INDEX "idx_cluster_first_p_29810b" ON "cluster" ("first_published_at");
        CREATE  INDEX "idx_cluster_weight_4e0093" ON "cluster" ("weight");"""
