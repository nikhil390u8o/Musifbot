import asyncio
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError
from pytgcalls import GroupCallFactory
import yt_dlp
import shutil
import uvicorn
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

# ---------- CONFIG ----------
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# -------- logging ----------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---------- client ----------
bot = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------- pytgcalls ----------
call_factory = GroupCallFactory(bot)
call_handler = call_factory.get_file_group_call()

# ---------- downloader options ----------
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(id)s.%(ext)s",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": True,
    "restrictfilenames": True,
}

os.makedirs("downloads", exist_ok=True)

async def homepage(request):
    return PlainTextResponse("Bot is alive!")

app = Starlette(routes=[
    Route("/", homepage)
])

async def download_audio(url: str) -> str:
    loop = asyncio.get_event_loop()

    def _dl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise RuntimeError("Failed to fetch info or download")
            filename = ydl.prepare_filename(info)
            base, ext = os.path.splitext(filename)
            mp3_file = f"{base}.mp3"
            if ext.lower() != ".mp3":
                if shutil.which("ffmpeg") is None:
                    if os.path.exists(mp3_file):
                        return mp3_file
                    raise RuntimeError("ffmpeg not found; cannot convert audio")
                os.system(f'ffmpeg -y -i "{filename}" -vn -acodec libmp3lame -ar 44100 -ac 2 -b:a 192k "{mp3_file}"')
                try:
                    if os.path.exists(mp3_file):
                        os.remove(filename)
                except:
                    pass
                return mp3_file
            else:
                return filename

    return await loop.run_in_executor(None, _dl)

async def ensure_chat_cached(chat_id: int, reply_message: Message) -> bool:
    try:
        await bot.get_chat(chat_id)
        return True
    except RPCError as e:
        await reply_message.reply_text("⚠️ I don't have access to this chat.")
        return False

@bot.on_message(filters.command("play") & (filters.group | filters.channel))
async def play_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /play <YouTube URL>")
        return
    url = message.command[1]
    chat_id = message.chat.id
    if not await ensure_chat_cached(chat_id, message):
        return
    try:
        await message.reply_text("⏳ Downloading audio...")
        filename = await download_audio(url)
        call_handler.input_filename = filename
        await call_handler.start(chat_id)
        await message.reply_text(f"🎶 Playing: `{os.path.basename(filename)}`", parse_mode="markdown")
    except Exception as e:
        logger.exception("Error in /play")
        await message.reply_text(f"❌ Error: {e}")

@bot.on_message(filters.command("stop") & (filters.group | filters.channel))
async def stop_command(client: Client, message: Message):
    try:
        await call_handler.leave_group_call(message.chat.id)
        await message.reply_text("⏹️ Stopped playing.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@bot.on_message(filters.command("ping"))
async def ping_cmd(client: Client, message: Message):
    await message.reply_text("🏓 Pong!")

async def start_all():
    await bot.start()
    logger.info("Bot started.")
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), log_level="info")
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), asyncio.Event().wait())

if __name__ == "__main__":
    try:
        asyncio.run(start_all())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down bot...")
