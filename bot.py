import os
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# --- Bot Config ---
API_ID =   
API_HASH = ""  
BOT_TOKEN = ""  
OWNER_ID =  
app = Client("video_thumb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Store data in memory ---
user_thumbs = {}  # user_id: photo_file_id
users_list = set()  # track all users


# --- Start Command ---
@app.on_message(filters.command("start"))
async def start_cmd(_, msg: Message):
    users_list.add(msg.from_user.id)
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
        " • Powered By: @World_Fastest_Bots"
    )


# --- Ping Command (for everyone) ---
@app.on_message(filters.command("ping"))
async def ping_cmd(_, msg: Message):
    start = time.time()
    m = await msg.reply_text("🏓 Pinging...")
    end = time.time()
    await m.edit_text(f"✅ Pong! `{round((end - start) * 1000)} ms`")


# --- Save Thumbnail ---
@app.on_message(filters.photo)
async def save_thumb(_, msg: Message):
    user_id = msg.from_user.id
    user_thumbs[user_id] = msg.photo.file_id
    users_list.add(user_id)
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
    users_list.add(user_id)

    if user_id not in user_thumbs:
        return await msg.reply_text("⚠️ You haven’t set any thumbnail.\n\nSend me a photo first!")

    thumb_id = user_thumbs[user_id]

    # Download video and thumbnail
    video_path = await msg.download()
    thumb_path = await app.download_media(thumb_id)

    # Caption in bold if exists
    if msg.caption:
        caption = f"**{msg.caption}**"
    else:
        caption = "** **"

    # Re-upload with custom thumbnail
    await msg.reply_video(
        video=video_path,
        thumb=thumb_path,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN
    )

    # Cleanup
    try:
        os.remove(video_path)
        os.remove(thumb_path)
    except:
        pass


# ============================
# --- Owner Only Commands ---
# ============================

def is_owner(func):
    async def wrapper(client, msg: Message):
        if msg.from_user.id != OWNER_ID:
            return await msg.reply_text("⛔ This command is for the owner only.")
        return await func(client, msg)
    return wrapper


@app.on_message(filters.command("users"))
@is_owner
async def get_users(_, msg: Message):
    await msg.reply_text(f"👥 Total Users: **{len(users_list)}**")


@app.on_message(filters.command("stats"))
@is_owner
async def stats_cmd(_, msg: Message):
    await msg.reply_text(
        f"📊 **Bot Stats:**\n\n"
        f"👥 Users: {len(users_list)}\n"
        f"🖼️ Thumbnails Saved: {len(user_thumbs)}"
    )


@app.on_message(filters.command("broadcast"))
@is_owner
async def broadcast_cmd(_, msg: Message):
    if not msg.reply_to_message:
        return await msg.reply_text("⚠️ Reply to a message to broadcast it.")

    sent, failed = 0, 0
    for user in list(users_list):
        try:
            await msg.reply_to_message.copy(user)
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.1)

    await msg.reply_text(f"📢 Broadcast finished!\n✅ Sent: {sent}\n❌ Failed: {failed}")


@app.on_message(filters.command("dbroadcast"))
@is_owner
async def dbroadcast_cmd(_, msg: Message):
    if len(msg.command) < 2 or not msg.reply_to_message:
        return await msg.reply_text("⚠️ Usage: `/dbroadcast <seconds>` (reply to a message).", parse_mode="markdown")

    try:
        duration = int(msg.command[1])
    except:
        return await msg.reply_text("❌ Invalid time. Use numbers only.")

    sent = 0
    for user in list(users_list):
        try:
            m = await msg.reply_to_message.copy(user)
            asyncio.create_task(delete_after(m, duration))
            sent += 1
        except:
            pass
        await asyncio.sleep(0.1)

    await msg.reply_text(f"📢 Timed broadcast sent to {sent} users. Auto-deletes after {duration} sec.")


async def delete_after(message: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass


@app.on_message(filters.command("restart"))
@is_owner
async def restart_cmd(_, msg: Message):
    await msg.reply_text("🔄 Restarting...")
    os.execl(sys.executable, sys.executable, *sys.argv)


print("🤖 Video Thumbnail Bot is running...")
app.run()
