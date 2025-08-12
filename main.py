import asyncio
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
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

# ---------- logging ----------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---------- bot ----------
bot = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
call_factory = GroupCallFactory(bot)
call_handler = call_factory.get_file_group_call()

# ---------- downloader ----------
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

async def download_audio(url: str) -> str:
    loop = asyncio.get_event_loop()
    def _dl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, ext = os.path.splitext(filename)
            mp3_file = f"{base}.mp3"
            if ext.lower() != ".mp3" and shutil.which("ffmpeg"):
                os.system(f'ffmpeg -y -i "{filename}" -vn -acodec libmp3lame -ar 44100 -ac 2 -b:a 192k "{mp3_file}"')
                os.remove(filename)
                return mp3_file
            return filename
    return await loop.run_in_executor(None, _dl)

# ---------- handlers ----------
@bot.on_message(filters.command("ping"))
async def ping_cmd(_, message: Message):
    await message.reply_text("🏓 Pong!")

@bot.on_message(filters.command("play") & (filters.group | filters.channel))
async def play_command(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /play <YouTube URL>")
    url = message.command[1]
    chat_id = message.chat.id
    await message.reply_text("⏳ Downloading audio...")
    filename = await download_audio(url)
    call_handler.input_filename = filename
    await call_handler.start(chat_id)
    await message.reply_text(f"🎶 Playing `{os.path.basename(filename)}`")

@bot.on_message(filters.command("stop") & (filters.group | filters.channel))
async def stop_command(_, message: Message):
    await call_handler.leave_group_call(message.chat.id)
    await message.reply_text("⏹️ Stopped.")

# ---------- Starlette ----------
async def homepage(request):
    return PlainTextResponse("Bot is alive!")

app = Starlette(routes=[Route("/", homepage)])

# ---------- run both ----------
async def main():
    await bot.start()
    logger.info("Bot started")
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), log_level="info")
    server = uvicorn.Server(config)
    
    # Run bot idle loop & web server together
    await asyncio.gather(
        server.serve(),
        bot.idle()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        asyncio.run(bot.stop())
