from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "cluster" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "title" TEXT NOT NULL,
    "summary" TEXT,
    "top_image" TEXT,
    "first_published_at" TIMESTAMPTZ NOT NULL,
    "last_updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "language" VARCHAR(8) NOT NULL  DEFAULT 'auto',
    "weight" INT NOT NULL  DEFAULT 0
);
        CREATE TABLE IF NOT EXISTS "source" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "kind" VARCHAR(16) NOT NULL,
    "domain" VARCHAR(255) NOT NULL,
    "status" VARCHAR(16) NOT NULL  DEFAULT 'active',
    "parser_profile" VARCHAR(32),
    "parse_overrides" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_source_kind_5cb74e" UNIQUE ("kind", "domain")
);
        CREATE TABLE IF NOT EXISTS "topic" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "code" VARCHAR(32) NOT NULL UNIQUE,
    "title" VARCHAR(128) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
        CREATE TABLE IF NOT EXISTS "article" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "url" TEXT NOT NULL,
    "url_canon" VARCHAR(4096),
    "title" TEXT NOT NULL,
    "summary" TEXT,
    "content_html" TEXT,
    "published_at" TIMESTAMPTZ NOT NULL,
    "language" VARCHAR(8) NOT NULL  DEFAULT 'auto',
    "content_fingerprint" VARCHAR(64),
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "cluster_id" INT NOT NULL REFERENCES "cluster" ("id") ON DELETE CASCADE,
    "source_id" INT NOT NULL REFERENCES "source" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_article_source__b66dd9" UNIQUE ("source_id", "url")
);
CREATE INDEX IF NOT EXISTS "idx_article_url_can_a2bf18" ON "article" ("url_canon");
CREATE INDEX IF NOT EXISTS "idx_article_publish_bd4e06" ON "article" ("published_at");
CREATE INDEX IF NOT EXISTS "idx_article_content_84d0d4" ON "article" ("content_fingerprint");
CREATE  INDEX "idx_article_cluster_300cfc" ON "article" ("cluster_id", "published_at");
CREATE  INDEX "idx_article_source__1429e8" ON "article" ("source_id", "published_at");
COMMENT ON COLUMN "article"."language" IS 'AUTO: auto\nRU: ru\nEN: en\nDE: de';
COMMENT ON TABLE "article" IS 'Нормализованный документ для выдачи.';

CREATE INDEX IF NOT EXISTS "idx_cluster_first_p_29810b" ON "cluster" ("first_published_at");
CREATE INDEX IF NOT EXISTS "idx_cluster_last_up_8dcdbb" ON "cluster" ("last_updated_at");
CREATE  INDEX "idx_cluster_weight_4e0093" ON "cluster" ("weight");
COMMENT ON COLUMN "cluster"."language" IS 'AUTO: auto\nRU: ru\nEN: en\nDE: de';
COMMENT ON TABLE "cluster" IS 'Инфоповод = группа похожих статей.';
        CREATE TABLE IF NOT EXISTS "clustertopic" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "score" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "is_primary" BOOL NOT NULL  DEFAULT False,
    "cluster_id" INT NOT NULL REFERENCES "cluster" ("id") ON DELETE CASCADE,
    "topic_id" INT NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_clustertopi_cluster_29b689" UNIQUE ("cluster_id", "topic_id")
);
COMMENT ON TABLE "clustertopic" IS 'M2M с весом/уверенностью классификатора';
        CREATE TABLE IF NOT EXISTS "rowdata" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "url_original" TEXT NOT NULL,
    "url_canon" VARCHAR(4096),
    "fetched_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "raw_content" TEXT,
    "raw_content_type" VARCHAR(8) NOT NULL  DEFAULT 'html',
    "raw_hash" VARCHAR(64),
    "source_id" INT NOT NULL REFERENCES "source" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_rowdata_url_can_9bff2b" ON "rowdata" ("url_canon");
CREATE INDEX IF NOT EXISTS "idx_rowdata_fetched_807444" ON "rowdata" ("fetched_at");
CREATE INDEX IF NOT EXISTS "idx_rowdata_raw_has_dcbe63" ON "rowdata" ("raw_hash");
CREATE  INDEX "idx_rowdata_source__4297bb" ON "rowdata" ("source_id", "fetched_at");
COMMENT ON COLUMN "rowdata"."raw_content_type" IS 'HTML: html\nTEXT: text\nJSON: json';
COMMENT ON TABLE "rowdata" IS 'Снимок скачанного ресурса.';

CREATE INDEX IF NOT EXISTS "idx_source_domain_049a7a" ON "source" ("domain");
COMMENT ON COLUMN "source"."kind" IS 'RSS: rss\nHTML: html\nJSONFEED: jsonfeed\nTELEGRAM: telegram';
COMMENT ON COLUMN "source"."status" IS 'ACTIVE: active\nVALIDATING: validating\nERROR: error\nDISABLED: disabled';
COMMENT ON TABLE "source" IS 'kind задаёт тип источника (rss/html/jsonfeed/telegram).';

COMMENT ON COLUMN "topic"."code" IS 'POLITICS: politics\nBUSINESS: business\nTECH: tech\nSCIENCE: science\nHEALTH: health\nSPORTS: sports\nENTERTAINMENT: entertainment\nWORLD: world\nLOCAL: local\nCULTURE: culture\nEDUCATION: education\nTRAVEL: travel\nAUTO: auto\nFINANCE: finance\nREAL_ESTATE: real_estate\nCRIME: crime\nWAR: war';
        CREATE TABLE IF NOT EXISTS "userarticlestate" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "read" BOOL NOT NULL  DEFAULT False,
    "bookmarked" BOOL NOT NULL  DEFAULT False,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "cluster_id" INT NOT NULL REFERENCES "cluster" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_userarticle_user_id_2998c0" UNIQUE ("user_id", "cluster_id")
);
        CREATE TABLE IF NOT EXISTS "usersource" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "status" VARCHAR(16) NOT NULL  DEFAULT 'validating',
    "poll_interval_sec" INT NOT NULL  DEFAULT 900,
    "rank" INT NOT NULL  DEFAULT 0,
    "labels" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "source_id" INT NOT NULL REFERENCES "source" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_usersource_user_id_beb7cc" UNIQUE ("user_id", "source_id")
);
COMMENT ON COLUMN "usersource"."status" IS 'ACTIVE: active\nERROR: error\nVALIDATING: validating';
COMMENT ON TABLE "usersource" IS 'Подключение источника пользователем.';
        CREATE TABLE IF NOT EXISTS "usertopicpref" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "weight" INT NOT NULL  DEFAULT 0,
    "topic_id" INT NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_usertopicpr_user_id_c5641f" UNIQUE ("user_id", "topic_id")
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "article";
        DROP TABLE IF EXISTS "cluster";
        DROP TABLE IF EXISTS "clustertopic";
        DROP TABLE IF EXISTS "rowdata";
        DROP TABLE IF EXISTS "source";
        DROP TABLE IF EXISTS "topic";
        DROP TABLE IF EXISTS "userarticlestate";
        DROP TABLE IF EXISTS "usersource";
        DROP TABLE IF EXISTS "usertopicpref";"""
