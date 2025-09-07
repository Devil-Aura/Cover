import os
import json
import logging
from telegram import Update, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError

BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # Set via environment variable
DATA_FILE = "user_data.json"

logging.basicConfig(level=logging.INFO, filename="bot.log")
logger = logging.getLogger(__name__)

# ---------------- Data Handling ----------------
def load_user_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

user_data = load_user_data()

# ---------------- Commands ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Welcome to Video Thumbnail Bot!\n\n"
        "1️⃣ Send a photo to save as your thumbnail.\n"
        "2️⃣ Send a video, and I’ll re-send it with that thumbnail.\n\n"
        "Commands:\n"
        "/show_cover - Show current thumbnail\n"
        "/del_cover - Delete saved thumbnail"
    )

async def show_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id in user_data and user_data[user_id].get("thumb"):
        await update.message.reply_photo(user_data[user_id]["thumb"], caption="📌 Your saved thumbnail")
    else:
        await update.message.reply_text("❌ No thumbnail found. Send a photo first.")

async def del_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id in user_data and user_data[user_id].get("thumb"):
        del user_data[user_id]["thumb"]
        save_user_data(user_data)
        await update.message.reply_text("🗑️ Thumbnail deleted.")
    else:
        await update.message.reply_text("❌ No thumbnail to delete.")

# ---------------- Handlers ----------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    photo = update.message.photo[-1]  # best quality
    file_id = photo.file_id

    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["thumb"] = file_id
    save_user_data(user_data)

    await update.message.reply_text("✅ Thumbnail saved!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    video = update.message.video

    if user_id not in user_data or not user_data[user_id].get("thumb"):
        return await update.message.reply_text("⚠️ No thumbnail set. Send a photo first.")

    caption = f"**{update.message.caption or ''}**"

    try:
        await context.bot.send_video(
            chat_id=update.message.chat_id,
            video=video.file_id,
            thumb=user_data[user_id]["thumb"],
            caption=caption,
            parse_mode="Markdown",
            supports_streaming=True
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ---------------- Main ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("show_cover", show_cover))
    app.add_handler(CommandHandler("del_cover", del_cover))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    print("✅ Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
