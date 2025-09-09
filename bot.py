import os
import sys
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
API_ID = 22768311
API_HASH = "702d8884f48b42e865425391432b3794"
BOT_TOKEN = "8201239010:AAHPS8LY5CfCyYoxd4-HQB7AAiwgM57l--Y"
OWNER_ID = 6040503076
FORCE_CHANNEL = -1002432405855  # Force sub channel ID

# Memory data (reset after restart)
admins = [OWNER_ID]
thumbs = {}      # user_id: path
chats = set()    # chats for broadcast
users = set()    # all unique users

# Init Bot
app = Client("cover-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= HELPERS =================
async def check_force_sub(client, user_id):
    try:
        member = await client.get_chat_member(FORCE_CHANNEL, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        return False
    return False


def is_admin(user_id):
    return user_id in admins


# ================= COMMANDS =================
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    user_id = message.from_user.id
    if not await check_force_sub(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/c/{str(FORCE_CHANNEL)[4:]}")]
        ])
        return await message.reply(
            "⚠️ You must join our channel to use this bot!",
            reply_markup=keyboard
        )

    users.add(user_id)
    chats.add(message.chat.id)
    await message.reply(
        f"👋 Hey {message.from_user.mention}!\n\n"
        "✨ I can send your videos with custom thumbnails (HD Covers).\n"
        "📌 Just send me a photo and it will be set as your thumbnail automatically.\n"
        "Then send a video/document and I’ll apply your cover!\n\n"
        "⚡ Fast • Simple • Powerful\n\n"
        "🔗 Powered By @World_Fastest_Bots",
    )


# ================= THUMBNAIL =================
@app.on_message(filters.photo)
async def auto_set_thumb(client, message: Message):
    user_id = message.from_user.id
    path = f"thumb_{user_id}.jpg"
    await message.download(file_name=path)
    thumbs[user_id] = path
    await message.reply("✅ Thumbnail saved automatically!")


@app.on_message(filters.command("show_cover"))
async def show_cover(client, message: Message):
    user_id = message.from_user.id
    if user_id in thumbs and os.path.exists(thumbs[user_id]):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Delete Thumbnail", callback_data=f"delthumb:{user_id}")]
        ])
        await message.reply_photo(thumbs[user_id], caption="🎭 Your Saved Thumbnail", reply_markup=keyboard)
    else:
        await message.reply("❌ No thumbnail found.")


@app.on_callback_query(filters.regex(r"^delthumb:(\d+)"))
async def delete_thumb(client, callback_query):
    user_id = int(callback_query.data.split(":")[1])
    if user_id in thumbs and os.path.exists(thumbs[user_id]):
        os.remove(thumbs[user_id])
        thumbs.pop(user_id)
        await callback_query.message.edit_caption("🗑️ Thumbnail deleted.")
    else:
        await callback_query.message.edit_caption("❌ No thumbnail to delete.")


# ================= MEDIA HANDLING =================
@app.on_message(filters.video | filters.document)
async def process_media(client, message: Message):
    user_id = message.from_user.id
    users.add(user_id)
    chats.add(message.chat.id)

    caption = message.caption or ""

    # Bold captions for admins only
    if is_admin(user_id) and caption:
        caption = f"**{caption}**"

    thumb_path = thumbs.get(user_id)

    try:
        if message.video:
            await client.send_video(
                chat_id=message.chat.id,
                video=message.video.file_id,
                caption=caption,
                cover=thumb_path if thumb_path else None,
            )
        elif message.document:
            await client.send_document(
                chat_id=message.chat.id,
                document=message.document.file_id,
                caption=caption,
                thumb=thumb_path if thumb_path else None,
            )
    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")


# ================= ADMIN SYSTEM =================
@app.on_message(filters.command("addadmin") & filters.user(OWNER_ID))
async def add_admin(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /addadmin <user_id>")
    try:
        new_admin = int(message.command[1])
        if new_admin not in admins:
            admins.append(new_admin)
            await message.reply(f"✅ Added {new_admin} as admin.")
        else:
            await message.reply("⚠️ Already an admin.")
    except:
        await message.reply("❌ Invalid ID.")


@app.on_message(filters.command("showadmin") & filters.user(OWNER_ID))
async def show_admin(client, message: Message):
    if not admins:
        return await message.reply("❌ No admins set.")
    admin_list = "\n".join([str(uid) for uid in admins])
    await message.reply(f"👑 Admins:\n{admin_list}")


@app.on_message(filters.command("removeadmin") & filters.user(OWNER_ID))
async def remove_admin(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /removeadmin <user_id>")
    try:
        rem_admin = int(message.command[1])
        if rem_admin in admins and rem_admin != OWNER_ID:
            admins.remove(rem_admin)
            await message.reply(f"🗑️ Removed {rem_admin} from admins.")
        else:
            await message.reply("⚠️ Cannot remove (maybe owner or not an admin).")
    except:
        await message.reply("❌ Invalid ID.")


# ================= OWNER ONLY EXTRA =================
@app.on_message(filters.command("users") & filters.user(OWNER_ID))
async def list_users(client, message: Message):
    await message.reply(f"👥 Total Unique Users: {len(users)}")


@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats(client, message: Message):
    stats_text = (
        f"📊 **Bot Stats**\n\n"
        f"👥 Users: `{len(users)}`\n"
        f"👑 Admins: `{len(admins)}`\n"
        f"💬 Chats: `{len(chats)}`\n"
        f"🖼️ Thumbnails Saved: `{len(thumbs)}`"
    )
    await message.reply(stats_text)


@app.on_message(filters.command("restart") & filters.user(OWNER_ID))
async def restart_bot(client, message: Message):
    await message.reply("♻️ Restarting bot...")
    os.execl(sys.executable, sys.executable, *sys.argv)


# ================= UTILS =================
@app.on_message(filters.command("ping"))
async def ping(client, message: Message):
    start = time.time()
    reply = await message.reply("🏓 Pong...")
    end = time.time()
    ms = int((end - start) * 1000)
    await reply.edit_text(f"🏓 Pong! `{ms}ms`")


@app.on_message(filters.command("dbroadcast") & filters.user(OWNER_ID))
async def dbroadcast(client, message: Message):
    if not message.reply_to_message:
        return await message.reply("⚠️ Reply to a message to broadcast.\n\nUsage: /dbroadcast <seconds>")

    if len(message.command) < 2:
        return await message.reply("⚠️ Provide time in seconds.\n\nUsage: /dbroadcast <seconds>")

    try:
        seconds = int(message.command[1])
    except:
        return await message.reply("❌ Invalid time.")

    sent_messages = []
    for chat_id in chats:
        try:
            msg = await message.reply_to_message.copy(chat_id)
            sent_messages.append((chat_id, msg.id))
        except:
            continue

    await message.reply(f"✅ Broadcast sent to {len(sent_messages)} chats. Will delete in {seconds}s.")

    await asyncio.sleep(seconds)

    for chat_id, msg_id in sent_messages:
        try:
            await client.delete_messages(chat_id, msg_id)
        except:
            continue


# ================= RUN =================
print("Bot Running...")
app.run()
