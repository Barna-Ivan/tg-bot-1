import logging
import os
import random
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from user_store import record_user

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_USER_ID = int(os.getenv("TARGET_USER_ID", "0"))
CHAT_ID = os.getenv("CHAT_ID")
GIF_FOLDER = Path(os.getenv("GIF_FOLDER", "gifs"))

GIF_EXTENSIONS = {".gif", ".mp4", ".webm"}


def _parse_chat_id(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    return int(value)


def get_gif_folder() -> Path:
    folder = GIF_FOLDER if GIF_FOLDER.is_absolute() else BASE_DIR / GIF_FOLDER
    return folder


def list_gifs(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in GIF_EXTENSIONS
    ]


def pick_random_gif() -> Optional[Path]:
    gifs = list_gifs(get_gif_folder())
    if not gifs:
        return None
    return random.choice(gifs)


def is_gif_message(message) -> bool:
    if message.animation:
        return True
    if message.document and message.document.mime_type == "image/gif":
        return True
    return False


def is_photo_message(message) -> bool:
    return bool(message.photo)


def is_sticker_message(message) -> bool:
    return bool(message.sticker)


def should_replace_message(message) -> bool:
    return (
        is_gif_message(message)
        or is_photo_message(message)
        or is_sticker_message(message)
    )


def get_media_type(message) -> str:
    if is_sticker_message(message):
        return "sticker"
    if is_photo_message(message):
        return "photo"
    return "GIF"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user or not chat:
        return

    record_user(user)

    if user.id != TARGET_USER_ID:
        return

    if not should_replace_message(message):
        return

    allowed_chat_id = _parse_chat_id(CHAT_ID)
    if allowed_chat_id is not None and chat.id != allowed_chat_id:
        return

    media_type = get_media_type(message)

    try:
        await message.delete()
        logger.info("Deleted %s from user %s in chat %s", media_type, user.id, chat.id)
    except Exception as exc:
        logger.error("Failed to delete message: %s", exc)
        return

    replacement = pick_random_gif()
    if not replacement:
        logger.warning("No GIF files in folder %s", get_gif_folder())
        return

    try:
        with replacement.open("rb") as gif_file:
            await chat.send_animation(animation=gif_file, filename=replacement.name)
        logger.info("Sent replacement GIF %s in chat %s", replacement.name, chat.id)
    except Exception as exc:
        logger.error("Failed to send replacement GIF: %s", exc)


def validate_config() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is required in .env")
    if not TARGET_USER_ID:
        raise SystemExit("TARGET_USER_ID is required in .env")

    folder = get_gif_folder()
    if not folder.is_dir():
        raise SystemExit(f"GIF folder not found: {folder}")

    gifs = list_gifs(folder)
    if not gifs:
        raise SystemExit(f"No GIF files in folder: {folder}")


def main() -> None:
    validate_config()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP | filters.ChatType.PRIVATE,
            handle_message,
        )
    )

    logger.info(
        "Bot started. Watching user ID: %s, GIF folder: %s",
        TARGET_USER_ID,
        get_gif_folder(),
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
