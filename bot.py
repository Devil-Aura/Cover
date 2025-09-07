import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# --- Bot Config ---
API_ID =   # Replace with your API_ID
API_HASH = ""  # Replace with your API_HASH
BOT_TOKEN = ""  # Replace with your Bot Token

app = Client("video_thumb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Store thumbnails in memory ---
user_thumbs = {}


# --- Start Command ---
@app.on_message(filters.command("start"))
async def start_cmd(_, msg: Message):
    await msg.reply_text(
        f"Hi {msg.from_user.mention}!\n\n"
        "Welcome to 🎬 **Video Cover/Thumbnail Bot.**\n\n"
        "- Add a custom cover/thumbnail to your videos instantly!\n\n"
        "**How it works 🤔**\n"
        "1️⃣ Send your photo (cover/thumbnail).\n"
        "2️⃣ Send your video, and the bot will add the cover automatically.\n\n"
        "✶ Commands:\n"
        "/show_cover - View your current cover\n"
        "/del_cover - Delete your saved cover\n\n"
        "👉 Use this bot to give your videos HD thumbnails before sharing!\n"
        " • 𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆:               @World_Fastest_Bots."
    )


# --- Save Thumbnail ---
@app.on_message(filters.photo)
async def save_thumb(_, msg: Message):
    user_id = msg.from_user.id
    user_thumbs[user_id] = msg.photo.file_id
    await msg.reply_text("✅ Your thumbnail has been saved! Now send me a video.")


# --- Show Thumbnail with Delete Button ---
@app.on_message(filters.command("show_cover"))
async def show_thumb(_, msg: Message):
    user_id = msg.from_user.id
    if user_id not in user_thumbs:
        return await msg.reply_text("❌ You don’t have any saved thumbnail.")

    await msg.reply_photo(
        user_thumbs[user_id],
        caption="🎬 Your current saved thumbnail.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Delete Cover ❌", callback_data="del_cover")]]
        )
    )


# --- Delete Thumbnail via Command ---
@app.on_message(filters.command("del_cover"))
async def delete_thumb(_, msg: Message):
    user_id = msg.from_user.id
    if user_id in user_thumbs:
        del user_thumbs[user_id]
        await msg.reply_text("🗑️ Thumbnail deleted successfully!")
    else:
        await msg.reply_text("❌ You don’t have any saved thumbnail.")


# --- Delete Thumbnail via Button ---
@app.on_callback_query(filters.regex("del_cover"))
async def delete_thumb_button(_, query):
    user_id = query.from_user.id
    if user_id in user_thumbs:
        del user_thumbs[user_id]
        await query.message.edit_caption("🗑️ Thumbnail deleted successfully!")
    else:
        await query.answer("❌ No thumbnail found.", show_alert=True)


# --- Apply Thumbnail to Video ---
@app.on_message(filters.video)
async def apply_thumb(_, msg: Message):
    user_id = msg.from_user.id

    if user_id not in user_thumbs:
        return await msg.reply_text("⚠️ You haven’t set any thumbnail.\n\nSend me a photo first!")

    thumb_id = user_thumbs[user_id]

    # Handle caption safely → keep original formatting if exists
    if msg.caption:
        try:
            caption = f"**{msg.caption}**"
        except Exception:
            caption = msg.caption
    else:
        caption = "** **"  # blank bold caption if none provided

    await msg.reply_video(
        msg.video.file_id,
        thumb=thumb_id,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN
    )


print("🤖 Video Thumbnail Bot is running...")
app.run()
