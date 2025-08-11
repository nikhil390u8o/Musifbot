import asyncio
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types.input_stream import InputAudioStream
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
import uvicorn
import youtube_dl

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(name)

# Configuration constants
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SESSION_STRING = os.environ.get("SESSION_STRING")
PORT = int(os.environ.get("PORT", 8000))

# Initialize Pyrogram client and PyTgCalls
app = Client(
    "music_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    session_string=SESSION_STRING
)
call_handler = PyTgCalls(app)

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

async def download_youtube_audio(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
        return filename

# Bot command handlers
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply_text("🎵 Music Bot is online! Use /play <YouTube URL> to play music in voice chat.")

@app.on_message(filters.command("play"))
async def play_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Please provide a YouTube URL. Usage: /play <YouTube URL>")
        return
    url = message.command[1]
    chat_id = message.chat.id
    try:
        # Download audio
        filename = await download_youtube_audio(url)
        # Join voice chat and play audio
        await call_handler.start()
        await call_handler.join_group_call(
            chat_id,
            InputAudioStream(filename),
            stream_type=StreamType().local_stream
        )
        await message.reply_text(f"🎶 Now playing: {filename}")
    except Exception as e:
        logger.error(f"Error playing audio: {e}")
        await message.reply_text(f"Error: {str(e)}")

@app.on_message(filters.command("stop"))
async def stop_command(client: Client, message: Message):
    chat_id = message.chat.id
    try:
        await call_handler.leave_group_call(chat_id)
        await message.reply_text("⏹️ Stopped playing music.")
    except Exception as e:
        logger.error(f"Error stopping audio: {e}")
        await message.reply_text(f"Error: {str(e)}")

# Webhook and health check handlers
async def telegram_webhook(request: Request) -> Response:
    """Handle incoming Telegram updates."""
    update = await request.json()
    await app.process
