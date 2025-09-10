import os
import json
import time
import sys
import asyncio
import logging
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG =================
API_ID = 22768311
API_HASH = "702d8884f48b42e865425391432b3794"
BOT_TOKEN = ""
OWNER_ID = 
DATA_FILE = "bot_data.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT = Client("thumbbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= STORAGE =================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "admins": [OWNER_ID]}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

def is_admin(user_id: int) -> bool:
    return user_id in data.get("admins", [])

# ================= START =================
@BOT.on_message(filters.command("start"))
async def start_cmd(client, m: Message):
    user_id = str(m.from_user.id)
    if user_id not in data["users"]:
        data["users"][user_id] = {"thumbnail": None}
        save_data()

    text = (
        "🎬 **Welcome to Video Thumbnail Changer Bot!**\n\n"
        "📌 Send me a **video**, and I’ll apply your saved thumbnail.\n"
        "✨ Send an **image** to save it as your default thumbnail.\n\n"
        "⚡ Powered by @World_Fastest_Bots"
    )
    await m.reply_text(text, quote=False)

# ================= PING =================
@BOT.on_message(filters.command("ping"))
async def ping_cmd(client, m: Message):
    start = time.time()
    msg = await m.reply_text("🏓 Pinging...", quote=False)
    end = time.time()
    await msg.edit(f"🏓 Pong! `{round((end - start) * 1000)}ms`")

# ================= THUMBNAIL =================
@BOT.on_message(filters.photo)
async def save_thumbnail(client, m: Message):
    user_id = str(m.from_user.id)
    file_id = m.photo.file_id
    data["users"][user_id]["thumbnail"] = file_id
    save_data()
    await m.reply_text("✅ Thumbnail saved successfully.", quote=False)

@BOT.on_message(filters.command("showthumb"))
async def show_thumb(client, m: Message):
    user_id = str(m.from_user.id)
    thumb = data["users"].get(user_id, {}).get("thumbnail")
    if thumb:
        await m.reply_photo(thumb, caption="🖼️ Your saved thumbnail.", quote=False)
    else:
        await m.reply_text("❌ You don't have any saved thumbnail.", quote=False)

@BOT.on_message(filters.command("deletethumb"))
async def delete_thumb(client, m: Message):
    user_id = str(m.from_user.id)
    if data["users"].get(user_id, {}).get("thumbnail"):
        data["users"][user_id]["thumbnail"] = None
        save_data()
        await m.reply_text("🗑️ Thumbnail deleted.", quote=False)
    else:
        await m.reply_text("❌ No thumbnail to delete.", quote=False)

# ================= VIDEO =================
@BOT.on_message(filters.video)
async def handle_video(client, m: Message):
    user_id = str(m.from_user.id)
    caption = m.caption or ""

    # Bold caption for admins
    if is_admin(m.from_user.id) and caption:
        caption = f"<b>{caption}</b>"

    thumb = data["users"].get(user_id, {}).get("thumbnail")

    try:
        await BOT.send_video(
            chat_id=m.chat.id,
            video=m.video.file_id,
            caption=caption,
            parse_mode="HTML",
            cover=thumb
        )
    except Exception as e:
        logger.error(f"Video Cover Error: {e}")
        await m.reply_text(f"⚠️ Error: {e}", quote=False)

# ================= ADMIN COMMANDS =================
@BOT.on_message(filters.command("addadmin"))
async def add_admin(client, m: Message):
    if m.from_user.id != OWNER_ID:
        return
    try:
        uid = int(m.text.split()[1])
        if uid not in data["admins"]:
            data["admins"].append(uid)
            save_data()
            await m.reply_text(f"✅ Added {uid} as admin.", quote=False)
        else:
            await m.reply_text("⚠️ Already an admin.", quote=False)
    except:
        await m.reply_text("❌ Usage: /addadmin user_id", quote=False)

@BOT.on_message(filters.command("removeadmin"))
async def remove_admin(client, m: Message):
    if m.from_user.id != OWNER_ID:
        return
    try:
        uid = int(m.text.split()[1])
        if uid in data["admins"]:
            data["admins"].remove(uid)
            save_data()
            await m.reply_text(f"✅ Removed {uid} from admins.", quote=False)
        else:
            await m.reply_text("⚠️ Not an admin.", quote=False)
    except:
        await m.reply_text("❌ Usage: /removeadmin user_id", quote=False)

@BOT.on_message(filters.command("showadmin"))
async def show_admins(client, m: Message):
    if m.from_user.id != OWNER_ID:
        return
    admins = "\n".join(str(a) for a in data["admins"])
    await m.reply_text(f"👮 Admins:\n{admins}", quote=False)

# ================= OWNER COMMANDS =================
@BOT.on_message(filters.command("users"))
async def list_users(client, m: Message):
    if m.from_user.id != OWNER_ID:
        return
    users = "\n".join(data["users"].keys())
    await m.reply_text(f"👤 Users:\n{users}", quote=False)

@BOT.on_message(filters.command("stats"))
async def stats(client, m: Message):
    if m.from_user.id != OWNER_ID:
        return
    total_users = len(data["users"])
    total_admins = len(data["admins"])
    await m.reply_text(f"📊 Stats:\n👤 Users: {total_users}\n👮 Admins: {total_admins}", quote=False)

@BOT.on_message(filters.command("restart"))
async def restart(client, m: Message):
    if m.from_user.id != OWNER_ID:
        return
    await m.reply_text("♻️ Restarting...", quote=False)
    os.execv(sys.executable, ["python3"] + sys.argv)

@BOT.on_message(filters.command("dbroadcast"))
async def dbroadcast(client, m: Message):
    if m.from_user.id != OWNER_ID:
        return
    try:
        parts = m.text.split(" ", 2)
        duration = int(parts[1])
        text = parts[2]
    except:
        return await m.reply_text("❌ Usage: /dbroadcast <seconds> <message>", quote=False)

    success, fail = 0, 0
    sent_msgs = []
    for uid in data["users"].keys():
        try:
            msg = await BOT.send_message(int(uid), text)
            sent_msgs.append((uid, msg.message_id))
            success += 1
        except:
            fail += 1

    await m.reply_text(f"✅ Broadcast done.\nSuccess: {success}\nFail: {fail}\n⏳ Will delete in {duration}s", quote=False)

    await asyncio.sleep(duration)
    for uid, msg_id in sent_msgs:
        try:
            await BOT.delete_messages(int(uid), msg_id)
        except:
            pass

# ================= RUN =================
BOT.run()
