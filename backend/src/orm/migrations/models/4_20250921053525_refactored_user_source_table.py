from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX "idx_rowdata_url_can_9bff2b";
        DROP INDEX "idx_rowdata_raw_has_dcbe63";
        DROP INDEX "idx_rowdata_source__4297bb";
        DROP INDEX "idx_cluster_weight_4e0093";
        DROP INDEX "idx_cluster_first_p_29810b";
        DROP INDEX "idx_cluster_last_up_8dcdbb";
        DROP INDEX "idx_article_source__1429e8";
        DROP INDEX "idx_article_url_can_a2bf18";
        DROP INDEX "idx_article_cluster_300cfc";
        ALTER TABLE "source" ALTER COLUMN "status" SET DEFAULT 'validating';
        ALTER TABLE "source" ALTER COLUMN "status" TYPE VARCHAR(16) USING "status"::VARCHAR(16);
        ALTER TABLE "usersource" ADD "is_enabled" BOOL NOT NULL  DEFAULT True;
        ALTER TABLE "usersource" DROP COLUMN "status";
        CREATE  INDEX "idx_article_cluster_300cfc" ON "article" ("cluster_id", "published_at");
        CREATE  INDEX "idx_article_url_can_a2bf18" ON "article" ("url_canon");
        CREATE  INDEX "idx_article_source__1429e8" ON "article" ("source_id", "published_at");
        CREATE  INDEX "idx_cluster_first_p_29810b" ON "cluster" ("first_published_at");
        CREATE  INDEX "idx_cluster_weight_4e0093" ON "cluster" ("weight");
        CREATE  INDEX "idx_cluster_last_up_8dcdbb" ON "cluster" ("last_updated_at");
        CREATE  INDEX "idx_rowdata_source__4297bb" ON "rowdata" ("source_id", "fetched_at");
        CREATE  INDEX "idx_rowdata_raw_has_dcbe63" ON "rowdata" ("raw_hash");
        CREATE  INDEX "idx_rowdata_url_can_9bff2b" ON "rowdata" ("url_canon");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX "idx_rowdata_url_can_9bff2b";
        DROP INDEX "idx_rowdata_raw_has_dcbe63";
        DROP INDEX "idx_rowdata_source__4297bb";
        DROP INDEX "idx_cluster_last_up_8dcdbb";
        DROP INDEX "idx_cluster_weight_4e0093";
        DROP INDEX "idx_cluster_first_p_29810b";
        DROP INDEX "idx_article_source__1429e8";
        DROP INDEX "idx_article_url_can_a2bf18";
        DROP INDEX "idx_article_cluster_300cfc";
        ALTER TABLE "source" ALTER COLUMN "status" SET DEFAULT 'active';
        ALTER TABLE "source" ALTER COLUMN "status" TYPE VARCHAR(16) USING "status"::VARCHAR(16);
        ALTER TABLE "usersource" ADD "status" VARCHAR(16) NOT NULL  DEFAULT 'validating';
        ALTER TABLE "usersource" DROP COLUMN "is_enabled";
        CREATE  INDEX "idx_article_cluster_300cfc" ON "article" ("cluster_id", "published_at");
        CREATE  INDEX "idx_article_url_can_a2bf18" ON "article" ("url_canon");
        CREATE  INDEX "idx_article_source__1429e8" ON "article" ("source_id", "published_at");
        CREATE  INDEX "idx_cluster_last_up_8dcdbb" ON "cluster" ("last_updated_at");
        CREATE  INDEX "idx_cluster_first_p_29810b" ON "cluster" ("first_published_at");
        CREATE  INDEX "idx_cluster_weight_4e0093" ON "cluster" ("weight");
        CREATE  INDEX "idx_rowdata_source__4297bb" ON "rowdata" ("source_id", "fetched_at");
        CREATE  INDEX "idx_rowdata_raw_has_dcbe63" ON "rowdata" ("raw_hash");
        CREATE  INDEX "idx_rowdata_url_can_9bff2b" ON "rowdata" ("url_canon");"""
