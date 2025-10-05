from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "phone_otps" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "phone" VARCHAR(32) NOT NULL,
    "code_hash" VARCHAR(128) NOT NULL,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "attempts" INT NOT NULL  DEFAULT 0,
    "last_sent_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_phone_otps_phone_ef3555" ON "phone_otps" ("phone");
        CREATE TABLE IF NOT EXISTS "user" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "phone" VARCHAR(32)  UNIQUE,
    "phone_verified_at" TIMESTAMPTZ,
    "name" VARCHAR(255),
    "avatar" VARCHAR(512),
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "phone_otps";
        DROP TABLE IF EXISTS "user";"""
