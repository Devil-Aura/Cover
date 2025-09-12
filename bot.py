import os
import json
import logging
from telegram import Update, MessageEntity
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError

BOT_TOKEN = ""  # Replace with your bot token
DATA_FILE = "user_data.json"

logging.basicConfig(level=logging.INFO, filename="bot.log")
logger = logging.getLogger(__name__)

# ============== Helpers for JSON storage ==============
def load_user_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading user data: {e}")
    return {}

def save_user_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

user_data = load_user_data()

# ============== Commands ==============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"cover": None}
        save_user_data(user_data)
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "📸 Send me a photo to save as your cover.\n"
        "🎥 Then send a video and I’ll apply it as cover.\n\n"
        "Commands:\n"
        "• /show_cover → Show current cover\n"
        "• /del_cover → Delete current cover"
    )

async def show_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cover = user_data.get(user_id, {}).get("cover")
    if cover:
        await update.message.reply_photo(cover, caption="📸 Your current cover")
    else:
        await update.message.reply_text("❌ No cover set. Send a photo first.")

async def del_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_data.get(user_id, {}).get("cover"):
        user_data[user_id]["cover"] = None
        save_user_data(user_data)
        await update.message.reply_text("🗑️ Cover deleted.")
    else:
        await update.message.reply_text("❌ No cover to delete.")

# ============== Handlers ==============
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save photo as cover automatically."""
    user_id = update.message.from_user.id
    photo = update.message.photo[-1]  # largest size
    user_data.setdefault(user_id, {})["cover"] = photo.file_id
    save_user_data(user_data)
    await update.message.reply_text("✅ New cover saved!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send video back with saved cover + bold caption."""
    user_id = update.message.from_user.id
    video = update.message.video
    if not video:
        return await update.message.reply_text("❌ Please send a valid video.")

    cover = user_data.get(user_id, {}).get("cover")
    caption = update.message.caption
    if caption:
        caption = f"<b>{caption}</b>"

    try:
        await context.bot.send_video(
            chat_id=update.message.chat_id,
            video=video.file_id,
            cover=cover,  # ⚠️ Only works if Bot API supports cover param
            caption=caption,
            parse_mode="HTML",
            supports_streaming=True
        )
        await update.message.reply_text("✅ Video sent with your cover applied!")
    except TelegramError as e:
        await update.message.reply_text(f"⚠️ Error sending video: {e}")

# ============== Main Runner ==============
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("show_cover", show_cover))
    app.add_handler(CommandHandler("del_cover", del_cover))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.run_polling()

if __name__ == "__main__":
    main()
