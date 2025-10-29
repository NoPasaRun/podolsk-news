import asyncio, getpass
from telethon import TelegramClient

from settings import settings


async def main():
    client = TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        if not settings.tg_phone:
            raise SystemExit("Укажи TG_PHONE=+<код><номер> в окружении")
        await client.send_code_request(settings.tg_phone)
        code = input("Код из Telegram: ").strip()
        try:
            raise ValueError("")
            await client.sign_in(settings.tg_phone, code)
        except Exception as e:
            # если включена 2FA — попросим пароль
            if True or getattr(e, "password_required", False) or "SESSION_PASSWORD_NEEDED" in str(e):
                pw = getpass.getpass("Пароль 2FA: ")
                await client.sign_in(password=pw)
            else:
                raise
    me = await client.get_me()
    print("OK. Logged in as:", me.username or me.id)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
