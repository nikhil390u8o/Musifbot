from pyrogram import Client

async def main():
    async with Client("music_bot", api_id="your_api_id", api_hash="your_api_hash") as app:
        session = await app.export_session_string()
        print(f"Session string: {session}")

if name == "main":
    import asyncio
    asyncio.run(main())
