from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX "idx_source_domain_049a7a";
        DROP INDEX "idx_cluster_first_p_29810b";
        DROP INDEX "idx_cluster_weight_4e0093";
        DROP INDEX "idx_cluster_last_up_8dcdbb";
        DROP INDEX "idx_article_url_can_a2bf18";
        DROP INDEX "idx_article_cluster_300cfc";
        DROP INDEX "idx_article_source__1429e8";
        ALTER TABLE "article" DROP COLUMN "content_html";
        ALTER TABLE "article" ALTER COLUMN "url_canon" SET NOT NULL;
        ALTER TABLE "article" ALTER COLUMN "url_canon" TYPE TEXT USING "url_canon"::TEXT;
        ALTER TABLE "source" DROP COLUMN "parser_profile";
        ALTER TABLE "source" DROP COLUMN "parse_overrides";
        ALTER TABLE "source" ALTER COLUMN "domain" TYPE TEXT USING "domain"::TEXT;
        ALTER TABLE "topic" ALTER COLUMN "code" TYPE VARCHAR(32) USING "code"::VARCHAR(32);
        ALTER TABLE "usersource" DROP COLUMN "labels";
        DROP TABLE IF EXISTS "rowdata";
        CREATE  INDEX "idx_article_source__1429e8" ON "article" ("source_id", "published_at");
        CREATE  INDEX "idx_article_cluster_300cfc" ON "article" ("cluster_id", "published_at");
        CREATE  INDEX "idx_cluster_weight_4e0093" ON "cluster" ("weight");
        CREATE  INDEX "idx_cluster_last_up_8dcdbb" ON "cluster" ("last_updated_at");
        CREATE  INDEX "idx_cluster_first_p_29810b" ON "cluster" ("first_published_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX "idx_cluster_first_p_29810b";
        DROP INDEX "idx_cluster_last_up_8dcdbb";
        DROP INDEX "idx_cluster_weight_4e0093";
        DROP INDEX "idx_article_cluster_300cfc";
        DROP INDEX "idx_article_source__1429e8";
        ALTER TABLE "topic" ALTER COLUMN "code" TYPE VARCHAR(32) USING "code"::VARCHAR(32);
        ALTER TABLE "source" ADD "parser_profile" VARCHAR(32);
        ALTER TABLE "source" ADD "parse_overrides" JSONB;
        ALTER TABLE "source" ALTER COLUMN "domain" TYPE VARCHAR(255) USING "domain"::VARCHAR(255);
        ALTER TABLE "article" ADD "content_html" TEXT;
        ALTER TABLE "article" ALTER COLUMN "url_canon" TYPE VARCHAR(4096) USING "url_canon"::VARCHAR(4096);
        ALTER TABLE "article" ALTER COLUMN "url_canon" DROP NOT NULL;
        ALTER TABLE "usersource" ADD "labels" JSONB NOT NULL;
        CREATE INDEX "idx_source_domain_049a7a" ON "source" ("domain");
        CREATE  INDEX "idx_article_source__1429e8" ON "article" ("source_id", "published_at");
        CREATE  INDEX "idx_article_cluster_300cfc" ON "article" ("cluster_id", "published_at");
        CREATE  INDEX "idx_article_url_can_a2bf18" ON "article" ("url_canon");
        CREATE INDEX "idx_article_url_can_a2bf18" ON "article" ("url_canon");
        CREATE  INDEX "idx_cluster_last_up_8dcdbb" ON "cluster" ("last_updated_at");
        CREATE  INDEX "idx_cluster_weight_4e0093" ON "cluster" ("weight");
        CREATE  INDEX "idx_cluster_first_p_29810b" ON "cluster" ("first_published_at");"""
