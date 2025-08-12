import asyncio
import os
import logging

from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import GroupCallFactory
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
import uvicorn
import youtube_dl

# Logging config
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Env vars
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", None)
PORT = int(os.environ.get("PORT", 8000))

# Pyrogram client
bot = Client(
    "music_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    session_string=SESSION_STRING
)

# PyTgCalls
call_factory = GroupCallFactory(bot)
call_handler = call_factory.get_file_group_call()

# YouTube download options
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

async def download_youtube_audio(url: str) -> str:
    """Download audio from YouTube and return local filename."""
    loop = asyncio.get_event_loop()
    def run_ydl():
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
            return filename
    filename = await loop.run_in_executor(None, run_ydl)
    return filename

@bot.on_message(filters.command("start"))
async def start_command(client, message):
    logger.info(f"Received /start from {message.from_user.id}")
    await message.reply_text("🎵 Music Bot is online!")

@bot.on_message(filters.command("play"))
async def play_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Please provide a YouTube URL. Usage: /play <YouTube URL>")
        return
    url = message.command[1]
    chat_id = message.chat.id
    try:
        await message.reply_text("⏳ Downloading audio, please wait...")
        filename = await download_youtube_audio(url)
        
        chat = await bot.get_chat(chat_id)           # Get chat object first
        call_handler.input_filename = filename        # Set audio file before start
        await call_handler.start(chat.id)             # Start call with valid chat id
        
        await message.reply_text(f"🎶 Now playing: {filename}")
    except Exception as e:
        logger.error(f"Error playing audio: {e}")
        await message.reply_text(f"Error: {str(e)}")

@bot.on_message(filters.command("stop"))
async def stop_command(client: Client, message: Message):
    chat_id = message.chat.id
    try:
        await call_handler.leave_group_call(chat_id)
        await message.reply_text("⏹️ Stopped playing music.")
    except Exception as e:
        logger.error(f"Error stopping audio: {e}")
        await message.reply_text(f"Error: {str(e)}")

# Health check endpoint
async def health(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

# Telegram webhook handler (optional if you want to use webhook)
async def telegram_webhook(request: Request) -> Response:
    update = await request.json()
    await bot.process_updates([update])
    return PlainTextResponse("OK")

# Starlette app routes
routes = [
    Route("/", health),
    Route("/webhook", telegram_webhook, methods=["POST"]),
]

web_app = Starlette(debug=True, routes=routes)

async def main():
    await bot.start()
    logger.info("Bot started!")
    # Run web server concurrently with bot
    config = uvicorn.Config(web_app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
