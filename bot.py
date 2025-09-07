import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# --- Config from ENV ---
API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", ""))

# --- Setup ---
os.makedirs("downloads", exist_ok=True)
app = Client("cover-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# --- Start ---
@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply(
        "🎬 **Video Cover/Thumbnail Bot**\n\n"
        "1. Send a photo (cover/thumbnail).\n"
        "2. Send a video, and I’ll add your cover automatically.\n\n"
        "✶ Commands:\n"
        "`/show_cover` - View your cover\n"
        "`/del_cover` - Delete your cover\n"
        "`/ping` - Check bot status\n"
        "~ @World_Fastest_Bots
    )


# --- Save Thumbnail ---
@app.on_message(filters.photo)
async def save_thumb(client, message: Message):
    user_id = str(message.from_user.id)
    path = f"downloads/{user_id}.jpg"
    await message.download(path)
    await message.reply("✅ Thumbnail saved!")


# --- Show Thumbnail ---
@app.on_message(filters.command("show_cover"))
async def show_cover(client, message: Message):
    user_id = str(message.from_user.id)
    path = f"downloads/{user_id}.jpg"
    if os.path.exists(path):
        btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Delete Cover", callback_data="delcover")]]
        )
        await message.reply_photo(path, caption="📌 Your saved cover:", reply_markup=btn)
    else:
        await message.reply("❌ No cover found. Send a photo to save one.")


# --- Delete Thumbnail ---
@app.on_message(filters.command("del_cover"))
async def del_cover(client, message: Message):
    user_id = str(message.from_user.id)
    path = f"downloads/{user_id}.jpg"
    if os.path.exists(path):
        os.remove(path)
        await message.reply("🗑️ Thumbnail deleted.")
    else:
        await message.reply("❌ No cover to delete.")


# --- Button Delete Cover ---
@app.on_callback_query(filters.regex("delcover"))
async def cb_delcover(client, callback_query):
    user_id = str(callback_query.from_user.id)
    path = f"downloads/{user_id}.jpg"
    if os.path.exists(path):
        os.remove(path)
        await callback_query.message.edit_caption("🗑️ Thumbnail deleted.")
    else:
        await callback_query.answer("❌ No cover found.", show_alert=True)


# --- Video/Doc Processing ---
@app.on_message(filters.video | filters.document)
async def process_media(client, message: Message):
    user_id = str(message.from_user.id)
    thumb_path = f"downloads/{user_id}.jpg"
    caption = f"**{message.caption or ''}**"

    if os.path.exists(thumb_path):
        media = message.video or message.document
        await message.reply_document(
            document=media.file_id,
            thumb=thumb_path,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.reply("⚠️ No custom thumbnail set. Send a photo first.")


# --- Ping ---
@app.on_message(filters.command("ping"))
async def ping_cmd(client, message: Message):
    await message.reply("🏓 Pong! Bot is alive.")


# --- Timed Broadcast (Owner only) ---
@app.on_message(filters.command("dbroadcast") & filters.user(OWNER_ID))
async def dbroadcast_cmd(client, message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not message.reply_to_message:
        return await message.reply("Usage: `/dbroadcast <seconds>` (reply to a message)", parse_mode=ParseMode.MARKDOWN)

    try:
        seconds = int(args[1])
    except ValueError:
        return await message.reply("❌ Invalid time. Use numbers only.")

    # Send broadcast to all chats the bot is in
    sent_msg = []
    async for dialog in app.get_dialogs():
        try:
            m = await message.reply_to_message.copy(dialog.chat.id)
            sent_msg.append((dialog.chat.id, m.id))
        except:
            pass

    await message.reply(f"✅ Broadcast sent to {len(sent_msg)} chats. Auto-delete in {seconds} sec.")

    await asyncio.sleep(seconds)

    # Delete messages
    for chat_id, msg_id in sent_msg:
        try:
            await app.delete_messages(chat_id, msg_id)
        except:
            pass


print("✅ Bot started...")
app.run()
