import os
import sys
import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

# ===================
# Config (from ENV)
# ===================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# ===================
# Memory storage
# ===================
user_thumbs = {}   # user_id: photo_file_id
users_list = set() # track all users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================
# Commands
# ===================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_list.add(update.effective_user.id)
    await update.message.reply_text(
        f"Hi {update.effective_user.mention_html()}!\n\n"
        "Welcome to 🎬 <b>Video Cover/Thumbnail Bot.</b>\n\n"
        "- Add a custom cover/thumbnail to your videos instantly!\n\n"
        "<b>How it works 🤔</b>\n"
        "1️⃣ Send your photo (cover/thumbnail).\n"
        "2️⃣ Send your video, and the bot will add the cover automatically.\n\n"
        "✶ Commands:\n"
        "/show_cover - View your current cover\n"
        "/del_cover - Delete your saved cover\n"
        "/ping - Check bot status\n\n"
        "👉 Use this bot to give your videos HD thumbnails before sharing!\n"
        " • Powered By: @World_Fastest_Bots",
        parse_mode="HTML"
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Pong! Bot is alive.")


async def save_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_thumbs[user_id] = update.message.photo[-1].file_id
    users_list.add(user_id)
    await update.message.reply_text("✅ Your thumbnail has been saved! Now send me a video.")


async def show_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_thumbs:
        return await update.message.reply_text("❌ You don’t have any saved thumbnail.")

    await update.message.reply_photo(
        user_thumbs[user_id],
        caption="🎬 Your current saved thumbnail.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Delete Cover ❌", callback_data="del_cover")]]
        )
    )


async def del_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_thumbs:
        del user_thumbs[user_id]
        await update.message.reply_text("🗑️ Thumbnail deleted successfully!")
    else:
        await update.message.reply_text("❌ You don’t have any saved thumbnail.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "del_cover":
        if user_id in user_thumbs:
            del user_thumbs[user_id]
            await query.edit_message_caption("🗑️ Thumbnail deleted successfully!")
        else:
            await query.answer("❌ No thumbnail found.", show_alert=True)


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users_list.add(user_id)

    if user_id not in user_thumbs:
        return await update.message.reply_text("⚠️ You haven’t set any thumbnail.\n\nSend me a photo first!")

    thumb_id = user_thumbs[user_id]

    caption = f"<b>{update.message.caption}</b>" if update.message.caption else "<b> </b>"

    await update.message.reply_video(
        video=update.message.video.file_id,
        thumb=thumb_id,
        caption=caption,
        parse_mode="HTML"
    )


# ===================
# Owner-only helpers
# ===================

def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            return await update.message.reply_text("⛔ This command is for the owner only.")
        return await func(update, context)
    return wrapper


@owner_only
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👥 Total Users: <b>{len(users_list)}</b>", parse_mode="HTML")


@owner_only
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 <b>Bot Stats:</b>\n\n"
        f"👥 Users: {len(users_list)}\n"
        f"🖼️ Thumbnails Saved: {len(user_thumbs)}",
        parse_mode="HTML"
    )


@owner_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply to a message to broadcast it.")

    sent, failed = 0, 0
    for user in list(users_list):
        try:
            await update.message.reply_to_message.copy(user)
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.1)

    await update.message.reply_text(f"📢 Broadcast finished!\n✅ Sent: {sent}\n❌ Failed: {failed}")


@owner_only
async def dbroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1 or not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Usage: /dbroadcast <seconds> (reply to a message)")

    try:
        duration = int(context.args[0])
    except:
        return await update.message.reply_text("❌ Invalid time. Use numbers only.")

    sent = 0
    for user in list(users_list):
        try:
            m = await update.message.reply_to_message.copy(user)
            context.job_queue.run_once(lambda _: m.delete(), duration)
            sent += 1
        except:
            pass
        await asyncio.sleep(0.1)

    await update.message.reply_text(f"📢 Timed broadcast sent to {sent} users. Auto-deletes after {duration} sec.")


@owner_only
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Restarting...")
    os.execl(sys.executable, sys.executable, *sys.argv)


# ===================
# Main
# ===================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("show_cover", show_thumb))
    app.add_handler(CommandHandler("del_cover", del_thumb))

    app.add_handler(MessageHandler(filters.PHOTO, save_thumb))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Owner only
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("dbroadcast", dbroadcast))
    app.add_handler(CommandHandler("restart", restart))

    print("🤖 Video Thumbnail Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
