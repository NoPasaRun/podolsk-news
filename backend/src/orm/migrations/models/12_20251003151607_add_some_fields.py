from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX "idx_cluster_first_p_29810b";
        DROP INDEX "idx_cluster_weight_4e0093";
        DROP INDEX "idx_cluster_last_up_8dcdbb";
        DROP INDEX "idx_article_cluster_300cfc";
        DROP INDEX "idx_article_source__1429e8";
        ALTER TABLE "article" ADD "image" TEXT;
        ALTER TABLE "cluster" DROP COLUMN "title";
        ALTER TABLE "cluster" DROP COLUMN "summary";
        ALTER TABLE "cluster" DROP COLUMN "top_image";
        CREATE  INDEX "idx_article_source__1429e8" ON "article" ("source_id", "published_at");
        CREATE  INDEX "idx_article_cluster_300cfc" ON "article" ("cluster_id", "published_at");
        CREATE  INDEX "idx_cluster_weight_4e0093" ON "cluster" ("weight");
        CREATE  INDEX "idx_cluster_first_p_29810b" ON "cluster" ("first_published_at");
        CREATE  INDEX "idx_cluster_last_up_8dcdbb" ON "cluster" ("last_updated_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX "idx_cluster_last_up_8dcdbb";
        DROP INDEX "idx_cluster_first_p_29810b";
        DROP INDEX "idx_cluster_weight_4e0093";
        DROP INDEX "idx_article_cluster_300cfc";
        DROP INDEX "idx_article_source__1429e8";
        ALTER TABLE "article" DROP COLUMN "image";
        ALTER TABLE "cluster" ADD "title" TEXT NOT NULL;
        ALTER TABLE "cluster" ADD "summary" TEXT;
        ALTER TABLE "cluster" ADD "top_image" TEXT;
        CREATE  INDEX "idx_article_source__1429e8" ON "article" ("source_id", "published_at");
        CREATE  INDEX "idx_article_cluster_300cfc" ON "article" ("cluster_id", "published_at");
        CREATE  INDEX "idx_cluster_last_up_8dcdbb" ON "cluster" ("last_updated_at");
        CREATE  INDEX "idx_cluster_weight_4e0093" ON "cluster" ("weight");
        CREATE  INDEX "idx_cluster_first_p_29810b" ON "cluster" ("first_published_at");"""
