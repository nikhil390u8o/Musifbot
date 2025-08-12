import asyncio
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError
from pytgcalls import GroupCallFactory
import yt_dlp
import shutil

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
    # postprocessor not used because we'll prefer ffmpeg later if needed
}

# ensure downloads dir exists
os.makedirs("downloads", exist_ok=True)


async def download_audio(url: str) -> str:
    """Download audio with yt_dlp and return the local filename (mp3 preferred)."""
    loop = asyncio.get_event_loop()

    def _dl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise RuntimeError("Failed to fetch info or download")
            # yt_dlp prepare filename
            filename = ydl.prepare_filename(info)
            # convert to mp3 filename if extension is not .mp3
            base, ext = os.path.splitext(filename)
            mp3_file = f"{base}.mp3"
            # If ffmpeg is available and source not mp3, convert
            if ext.lower() != ".mp3":
                # try ffmpeg conversion (overwrite if exists)
                if shutil.which("ffmpeg") is None:
                    # if no ffmpeg, try to find an existing mp3 (some ydl formats may already be mp3)
                    if os.path.exists(mp3_file):
                        return mp3_file
                    raise RuntimeError("ffmpeg not found; cannot convert audio to mp3")
                # convert
                cmd = f'ffmpeg -y -i "{filename}" -vn -acodec libmp3lame -ar 44100 -ac 2 -b:a 192k "{mp3_file}"'
                os.system(cmd)
                # optional: remove original file
                try:
                    if os.path.exists(mp3_file):
                        os.remove(filename)
                except Exception:
                    pass
                return mp3_file
            else:
                return filename

    filename = await loop.run_in_executor(None, _dl)
    return filename


async def ensure_chat_cached(chat_id: int, reply_message: Message) -> bool:
    """Try to resolve chat (cache peer). Return True if OK, else reply and return False."""
    try:
        chat = await bot.get_chat(chat_id)
        logger.info(f"Resolved chat {chat.id} / {getattr(chat, 'title', 'private')}")
        return True
    except RPCError as e:
        logger.warning(f"Could not get chat {chat_id}: {e}")
        await reply_message.reply_text("⚠️ I don't have access to this chat. Add me & give voice permissions.")
        return False
    except ValueError as e:
        logger.warning(f"Invalid chat id {chat_id}: {e}")
        await reply_message.reply_text("⚠️ Invalid chat id.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error resolving chat {chat_id}: {e}")
        await reply_message.reply_text("⚠️ Unexpected error while accessing the chat.")
        return False


@bot.on_message(filters.command("play") & (filters.group | filters.channel))
async def play_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /play <YouTube URL>")
        return
    url = message.command[1]
    chat_id = message.chat.id
    logger.info(f"Play requested in {chat_id} -> {url}")

    # ensure chat access to avoid Peer id invalid
    ok = await ensure_chat_cached(chat_id, message)
    if not ok:
        return

    try:
        await message.reply_text("⏳ Downloading audio... please wait.")
        filename = await download_audio(url)
        logger.info(f"Downloaded audio: {filename}")

        # set file and start group call
        call_handler.input_filename = filename
        await call_handler.start(chat_id)
        await message.reply_text(f"🎶 Playing now: `{os.path.basename(filename)}`", parse_mode="markdown")
    except Exception as e:
        logger.exception("Error in /play")
        await message.reply_text(f"❌ Error while trying to play: {e}")


@bot.on_message(filters.command("stop") & (filters.group | filters.channel))
async def stop_command(client: Client, message: Message):
    chat_id = message.chat.id
    logger.info(f"Stop requested in {chat_id}")
    try:
        await call_handler.leave_group_call(chat_id)
        await message.reply_text("⏹️ Stopped playing.")
    except Exception as e:
        logger.exception("Error in /stop")
        await message.reply_text(f"❌ Error while stopping: {e}")


@bot.on_message(filters.command("ping"))
async def ping_cmd(client: Client, message: Message):
    try:
        await message.reply_text("🏓 Pong!")
    except Exception:
        pass


async def main():
    # Start bot and stay alive (polling)
    await bot.start()
    logger.info("Bot started (polling). Waiting for commands...")
    # Keep the process alive; Pyrogram internally receives updates while running
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot shutting down...")
        try:
            asyncio.run(bot.stop())
        except Exception:
            pass
