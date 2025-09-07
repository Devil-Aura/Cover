import asyncio
import os
import sys
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# --- Bot Config ---
API_ID =   
API_HASH = ""  
BOT_TOKEN = ""  # Replace with your Bot Token
OWNER_ID =   # Replace with your Telegram User ID

app = Client("video_thumb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Store thumbnails & users in memory ---
user_thumbs = {}
all_users = set()


# --- Start Command ---
@app.on_message(filters.command("start"))
async def start_cmd(_, msg: Message):
    user_id = msg.from_user.id
    all_users.add(user_id)

    await msg.reply_text(
        f"Hi {msg.from_user.mention}!\n\n"
        "Welcome to 🎬 **Video Cover/Thumbnail Bot.**\n\n"
        "- Add a custom cover/thumbnail to your videos instantly!\n\n"
        "**How it works 🤔**\n"
        "1️⃣ Send your photo (cover/thumbnail).\n"
        "2️⃣ Send your video, and the bot will add the cover automatically.\n\n"
        "✶ Commands:\n"
        "/show_cover - View your current cover\n"
        "/del_cover - Delete your saved cover\n"
        "/ping - Check bot status\n\n"
        "👉 Use this bot to give your videos HD thumbnails before sharing!\n"
        " • 𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆: @World_Fastest_Bots."
    )


# --- Save Thumbnail ---
@app.on_message(filters.photo)
async def save_thumb(_, msg: Message):
    user_id = msg.from_user.id
    all_users.add(user_id)
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
    all_users.add(user_id)

    if user_id not in user_thumbs:
        return await msg.reply_text("⚠️ You haven’t set any thumbnail.\n\nSend me a photo first!")

    thumb_id = user_thumbs[user_id]

    # Handle caption safely
    caption = msg.caption or ""
    if caption.startswith("**") and caption.endswith("**"):
        final_caption = caption  # already bold
    elif caption.strip():
        final_caption = f"**{caption}**"
    else:
        final_caption = "** **"  # empty bold caption

    await msg.reply_video(
        msg.video.file_id,
        thumb=thumb_id,
        caption=final_caption,
        parse_mode=ParseMode.MARKDOWN
    )


# =========================
#       GENERAL COMMANDS
# =========================

# --- Ping (everyone can use) ---
@app.on_message(filters.command("ping"))
async def ping_cmd(_, msg: Message):
    start = time.time()
    reply = await msg.reply_text("🏓 Pinging...")
    end = time.time()
    await reply.edit_text(f"🏓 Pong! `{round((end - start) * 1000)}ms`")


# =========================
#       OWNER COMMANDS
# =========================

def owner_only(func):
    async def wrapper(client, msg: Message):
        if msg.from_user.id != OWNER_ID:
            return await msg.reply_text("❌ You are not authorized to use this command.")
        return await func(client, msg)
    return wrapper


# --- Users ---
@app.on_message(filters.command("users"))
@owner_only
async def users_cmd(_, msg: Message):
    await msg.reply_text(f"👥 Total users: `{len(all_users)}`")


# --- Stats ---
@app.on_message(filters.command("stats"))
@owner_only
async def stats_cmd(_, msg: Message):
    thumbs_count = len(user_thumbs)
    users_count = len(all_users)
    await msg.reply_text(
        f"📊 **Bot Stats:**\n\n"
        f"👥 Total Users: `{users_count}`\n"
        f"🖼️ Users with Thumbnails: `{thumbs_count}`"
    )


# --- Broadcast ---
@app.on_message(filters.command("broadcast"))
@owner_only
async def broadcast_cmd(_, msg: Message):
    if not msg.reply_to_message:
        return await msg.reply_text("⚠️ Reply to a message to broadcast.")
    
    sent = 0
    failed = 0
    for user in list(all_users):
        try:
            await msg.reply_to_message.copy(user)
            sent += 1
        except Exception:
            failed += 1
    await msg.reply_text(f"📢 Broadcast done.\n✅ Sent: {sent}\n❌ Failed: {failed}")


# --- Timed Broadcast (Delete After X Seconds) ---
@app.on_message(filters.command("dbroadcast"))
@owner_only
async def dbroadcast_cmd(_, msg: Message):
    if not msg.reply_to_message:
        return await msg.reply_text("⚠️ Reply to a message to broadcast with delete timer.\n\nUsage: `/dbroadcast 30`")
    
    try:
        seconds = int(msg.text.split(maxsplit=1)[1])
    except Exception:
        return await msg.reply_text("⚠️ Invalid usage.\n\nExample: `/dbroadcast 30` (auto delete in 30s)")

    sent = 0
    failed = 0
    for user in list(all_users):
        try:
            sent_msg = await msg.reply_to_message.copy(user)
            sent += 1
            # schedule deletion
            asyncio.create_task(delete_after(sent_msg, seconds))
        except Exception:
            failed += 1

    await msg.reply_text(f"📢 Timed Broadcast done.\n✅ Sent: {sent}\n❌ Failed: {failed}\n🕒 Auto delete after {seconds}s")


async def delete_after(message: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


# --- Restart ---
@app.on_message(filters.command("restart"))
@owner_only
async def restart_cmd(_, msg: Message):
    await msg.reply_text("♻️ Restarting bot...")
    os.execv(sys.executable, ["python"] + sys.argv)


print("🤖 Video Thumbnail Bot is running...")
app.run()
