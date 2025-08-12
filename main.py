import asyncio
import logging
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
import uvicorn

# ===== Logging =====
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ===== Bot Config =====
API_ID = int("20898349")  # your API_ID
API_HASH = "9fdb830d1e435b785f536247f49e7d87"
BOT_TOKEN = "8120599964:AAEVkZP8yCJMWmRZV1a7N7WwaPxq5yVGW_A"

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
call = PyTgCalls(bot)

# ===== Starlette Web Server =====
async def homepage(request):
    return PlainTextResponse("Bot is alive!")

app = Starlette(routes=[Route("/", homepage)])

# ===== Pyrogram Handlers =====
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply("Hello! I'm working fine ✅")

# ===== Main Startup =====
async def start_all():
    # Start Pyrogram
    await bot.start()
    logging.info("Pyrogram started ✅")

    # Start PyTgCalls
    await call.start()
    logging.info("PyTgCalls started ✅")

    # Start Uvicorn (Starlette)
    config = uvicorn.Config(app, host="0.0.0.0", port=10000, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await start_all()

if __name__ == "__main__":
    asyncio.run(main())
