import os
import json
import logging
from telegram import Update, MessageEntity
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
)
from telegram.error import TelegramError

BOT_TOKEN = ""  # Replace with your actual bot token
FORCE_SUB_CHANNEL = -1002432405855  # Your force sub channel ID
DATA_FILE = "user_data.json"

# Setup logging - only errors
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot_errors.log")]
)
logger = logging.getLogger(__name__)

# Load and save user data
def load_user_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_user_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save user data: {e}")

user_data = load_user_data()

# Force subscription check
async def is_user_joined(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has joined the force sub channel"""
    try:
        member = await context.bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {
            "thumbnail": None,
            "state": "idle"
        }
        save_user_data(user_data)
    
    welcome_text = (
        "🎬 <b>Video Cover Bot</b>\n\n"
        "✨ <b>Free • Fast • Reliable</b>\n\n"
        "📸 <b>How to use:</b>\n"
        "• Send a photo - it will be saved as thumbnail\n"
        "• Send any video - thumbnail will be added automatically\n"
        "• Works for all your videos\n\n"
        "🛠 <b>Commands:</b>\n"
        "• /mythumb - See your saved thumbnail\n"
        "• /delthumb - Remove your thumbnail\n"
        "• /help - Get help guide\n\n"
        "⚡ <b>Powered by:</b> @World_Fastest_Bots\n\n"
        "💬 <b>Need help?</b> Feel free to contact us!"
    )
    
    await update.message.reply_text(welcome_text, parse_mode='HTML')

# Handle photo message - automatically save as thumbnail
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Check force subscription for photo processing
    if not await is_user_joined(user_id, context):
        force_sub_text = (
            "🔒 <b>Join Required</b>\n\n"
            "To use this bot, please join our channel first.\n\n"
            "⚡ <b>@World_Fastest_Bots</b>\n\n"
            "Join our channel and try again."
        )
        await update.message.reply_text(force_sub_text, parse_mode='HTML')
        return
    
    photos = update.message.photo
    largest_photo = max(photos, key=lambda p: p.file_size)
    
    if user_id not in user_data:
        user_data[user_id] = {"thumbnail": None, "state": "idle"}
    
    if user_data[user_id].get("state") == "waiting_for_image":
        smallest = min(photos, key=lambda p: p.file_size)
        
        if smallest.file_size > 200 * 1024 or smallest.width > 320 or smallest.height > 320:
            await update.message.reply_text("❌ Please send a smaller image (under 200KB and 320x320 pixels).")
            return
        
        user_data[user_id]["image_file_id"] = largest_photo.file_id
        save_user_data(user_data)

        try:
            entities = [
                MessageEntity(
                    type=e["type"],
                    offset=e["offset"],
                    length=e["length"],
                    user=e.get("user")
                ) for e in user_data[user_id]["caption_entities"]
            ] if user_data[user_id].get("caption_entities") else None

            # Send video with cover as reply to original video
            await context.bot.send_video(
                chat_id=update.message.chat_id,
                video=user_data[user_id]["video_file_id"],
                cover=user_data[user_id]["image_file_id"],
                caption=user_data[user_id]["video_caption"],
                caption_entities=entities,
                supports_streaming=True,
                has_spoiler=user_data[user_id].get("has_spoiler", False),
                reply_to_message_id=update.message.message_id - 1  # Reply to the video message
            )
            # No success message sent - only the video is sent as reply

            user_data[user_id]["thumbnail"] = largest_photo.file_id

        except TelegramError as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

        user_data[user_id] = {
            "thumbnail": user_data[user_id]["thumbnail"],
            "state": "idle",
            "video_file_id": None,
            "video_caption": None,
            "caption_entities": None,
            "image_file_id": None,
            "has_spoiler": False
        }
        
    else:
        user_data[user_id]["thumbnail"] = largest_photo.file_id
        user_data[user_id]["state"] = "idle"
        await update.message.reply_text("✅ Thumbnail saved! Now send me a video.")
    
    save_user_data(user_data)

# Handle video message
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Check force subscription for video processing
    if not await is_user_joined(user_id, context):
        force_sub_text = (
            "🔒 <b>Join Required</b>\n\n"
            "To use this bot, please join our channel first.\n\n"
            "⚡ <b>@World_Fastest_Bots</b>\n\n"
            "Join our channel and try again."
        )
        await update.message.reply_text(force_sub_text, parse_mode='HTML')
        return
    
    video = update.message.video
    if not video:
        return await update.message.reply_text("❌ Please send a valid video.")

    saved_thumbnail = user_data.get(user_id, {}).get("thumbnail")
    
    if saved_thumbnail:
        try:
            # Send video with saved thumbnail as reply to original video
            await context.bot.send_video(
                chat_id=update.message.chat_id,
                video=video.file_id,
                cover=saved_thumbnail,
                caption=update.message.caption,
                caption_entities=update.message.caption_entities,
                supports_streaming=True,
                reply_to_message_id=update.message.message_id  # Reply to the original video
            )
            # No success message sent - only the video is sent as reply
            return
            
        except TelegramError as e:
            await update.message.reply_text("❌ Error using saved thumbnail. Please send a photo first.")
            return

    caption_entities = [
        {
            "offset": e.offset,
            "length": e.length,
            "type": e.type,
            "user": e.user.to_dict() if e.type == "text_mention" else None
        }
        for e in update.message.caption_entities or []
    ]
    
    if user_id not in user_data:
        user_data[user_id] = {"thumbnail": None, "state": "idle"}
    
    user_data[user_id].update({
        "state": "waiting_for_image",
        "video_file_id": video.file_id,
        "video_caption": update.message.caption,
        "caption_entities": caption_entities,
        "image_file_id": None,
        "has_spoiler": user_data[user_id].get("has_spoiler", False)
    })
    
    save_user_data(user_data)
    await update.message.reply_text("✅ Video received! Now send me a photo for the cover.")

# Thumbnail management commands
async def my_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    thumbnail = user_data.get(user_id, {}).get("thumbnail")
    
    if thumbnail:
        try:
            await update.message.reply_photo(
                photo=thumbnail,
                caption="🖼️ <b>Your Current Thumbnail</b>\n\nThis image will be added to all your videos automatically.\n\nUse /delthumb to delete this current thumbnail.",
                parse_mode='HTML'
            )
        except Exception:
            await update.message.reply_text("❌ Can't load thumbnail. Please set a new one.")
    else:
        await update.message.reply_text("❌ No thumbnail saved yet. Send me a photo to set one.")

async def delete_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id in user_data and user_data[user_id].get("thumbnail"):
        user_data[user_id]["thumbnail"] = None
        save_user_data(user_data)
        await update.message.reply_text("✅ Thumbnail removed successfully!")
    else:
        await update.message.reply_text("❌ No thumbnail found to delete.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🎬 <b>Video Cover Bot - Help Guide</b>\n\n"
        "✨ <b>Free • Fast • Reliable</b>\n\n"
        "📖 <b>How to use this bot:</b>\n"
        "1. <b>Send a photo</b> - It will be saved as your thumbnail\n"
        "2. <b>Send a video</b> - The thumbnail will be added automatically\n"
        "3. <b>Repeat</b> - Same thumbnail works for all future videos\n\n"
        "🛠 <b>Commands:</b>\n"
        "• /start - Start the bot\n"
        "• /mythumb - See your thumbnail\n"
        "• /delthumb - Remove thumbnail\n"
        "• /help - Show this guide\n\n"
        "💡 <b>Tips:</b>\n"
        "• Use clear photos for best results\n"
        "• Thumbnail works for all videos\n"
        "• No need to resend photos\n\n"
        "⚡ <b>Powered by:</b> @World_Fastest_Bots\n\n"
        "💬 <b>Need help or have feedback?</b> Feel free to reach us!"
    )
    
    await update.message.reply_text(help_text, parse_mode='HTML')

# Callback handler for force sub check (simplified)
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if query.data == "check_join":
        if await is_user_joined(user.id, context):
            await query.edit_message_text(
                "✅ <b>Welcome!</b>\n\n"
                "You can now use the bot.\n\n"
                "Send a photo to set as thumbnail, then send any video!\n\n"
                "⚡ <b>Powered by:</b> @World_Fastest_Bots\n\n"
                "💬 <b>Need help?</b> Contact us anytime!",
                parse_mode='HTML'
            )
        else:
            await query.answer("Please join the channel first!", show_alert=True)

# Main runner
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mythumb", my_thumbnail))
    app.add_handler(CommandHandler("delthumb", delete_thumbnail))
    app.add_handler(CommandHandler("help", help_command))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("🎬 Video Cover Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
