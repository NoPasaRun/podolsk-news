from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX "idx_cluster_last_up_8dcdbb";
        DROP INDEX "idx_cluster_weight_4e0093";
        DROP INDEX "idx_cluster_first_p_29810b";
        DROP INDEX "idx_article_cluster_300cfc";
        DROP INDEX "idx_article_source__1429e8";
        ALTER TABLE "source" ADD "is_default" BOOL NOT NULL  DEFAULT False;
        ALTER TABLE "source" ALTER COLUMN "kind" TYPE VARCHAR(16) USING "kind"::VARCHAR(16);
        CREATE  INDEX "idx_article_cluster_300cfc" ON "article" ("cluster_id", "published_at");
        CREATE  INDEX "idx_article_source__1429e8" ON "article" ("source_id", "published_at");
        CREATE  INDEX "idx_cluster_weight_4e0093" ON "cluster" ("weight");
        CREATE  INDEX "idx_cluster_first_p_29810b" ON "cluster" ("first_published_at");
        CREATE  INDEX "idx_cluster_last_up_8dcdbb" ON "cluster" ("last_updated_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX "idx_cluster_last_up_8dcdbb";
        DROP INDEX "idx_cluster_first_p_29810b";
        DROP INDEX "idx_cluster_weight_4e0093";
        DROP INDEX "idx_article_source__1429e8";
        DROP INDEX "idx_article_cluster_300cfc";
        ALTER TABLE "source" DROP COLUMN "is_default";
        ALTER TABLE "source" ALTER COLUMN "kind" TYPE VARCHAR(16) USING "kind"::VARCHAR(16);
        CREATE  INDEX "idx_article_source__1429e8" ON "article" ("source_id", "published_at");
        CREATE  INDEX "idx_article_cluster_300cfc" ON "article" ("cluster_id", "published_at");
        CREATE  INDEX "idx_cluster_first_p_29810b" ON "cluster" ("first_published_at");
        CREATE  INDEX "idx_cluster_weight_4e0093" ON "cluster" ("weight");
        CREATE  INDEX "idx_cluster_last_up_8dcdbb" ON "cluster" ("last_updated_at");"""
