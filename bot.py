import os
import json
import logging
import asyncio
import sys
import time
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ================= CONFIG =================
BOT_TOKEN = ""
OWNER_ID = 
DATA_FILE = "bot_data.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CoverBot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ================ DATA STORAGE =================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "admins": [OWNER_ID]}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

def ensure_user(uid: int):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"thumb": None}
        save_data()

def is_owner(uid: int):
    return uid == OWNER_ID

def is_admin(uid: int):
    return uid in data["admins"]

# ================= START =================
@dp.message_handler(commands=["start"])
async def start_cmd(m: types.Message):
    ensure_user(m.from_user.id)
    text = (
        "🎬 <b>Welcome to Video Cover Changer Bot!</b>\n\n"
        "📌 Send me a <b>video</b> and I’ll apply your saved cover.\n"
        "🖼️ Send an <b>image</b> to set as your cover.\n\n"
        "⚡ Powered by @World_Fastest_Bots"
    )
    await m.answer(text, parse_mode="HTML")

# ================= PING =================
@dp.message_handler(commands=["ping"])
async def ping_cmd(m: types.Message):
    start = time.time()
    sent = await m.answer("🏓 Pong...")
    end = time.time()
    await sent.edit_text(f"🏓 Pong! `{int((end-start)*1000)} ms`", parse_mode="Markdown")

# ================= THUMBNAIL =================
@dp.message_handler(content_types=["photo"])
async def save_thumbnail(m: types.Message):
    uid = str(m.from_user.id)
    ensure_user(uid)
    file_id = m.photo[-1].file_id
    data["users"][uid]["thumb"] = file_id
    save_data()
    await m.reply("✅ Cover saved! Now send me a video.")

@dp.message_handler(commands=["show_cover"])
async def show_cover(m: types.Message):
    uid = str(m.from_user.id)
    ensure_user(uid)
    thumb = data["users"][uid].get("thumb")
    if thumb:
        await m.answer_photo(thumb, caption="🖼️ This is your current cover.")
    else:
        await m.reply("❌ You don’t have a saved cover.")

@dp.message_handler(commands=["delete_cover"])
async def delete_cover(m: types.Message):
    uid = str(m.from_user.id)
    ensure_user(uid)
    data["users"][uid]["thumb"] = None
    save_data()
    await m.reply("🗑️ Cover deleted.")

# ================= VIDEO =================
@dp.message_handler(content_types=["video"])
async def handle_video(m: types.Message):
    uid = str(m.from_user.id)
    ensure_user(uid)
    thumbnail = data["users"][uid].get("thumb")

    caption = m.caption or ""
    if is_owner(m.from_user.id) or is_admin(m.from_user.id):
        caption = f"<b>{caption}</b>" if caption else None
        parse_mode = "HTML"
    else:
        parse_mode = None

    try:
        await bot.send_video(
            chat_id=m.chat.id,
            video=m.video.file_id,
            caption=caption,
            parse_mode=parse_mode,
            cover=thumbnail,  # your requested param
        )
    except Exception as e:
        logger.error(f"Video Cover Error: {e}")
        await m.reply(f"⚠️ Error applying cover: {e}")

# ================= ADMIN COMMANDS =================
@dp.message_handler(commands=["addadmin"])
async def add_admin(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    try:
        uid = int(m.get_args())
        if uid not in data["admins"]:
            data["admins"].append(uid)
            save_data()
            await m.reply(f"✅ Added {uid} as admin.")
        else:
            await m.reply("⚠️ Already admin.")
    except:
        await m.reply("❌ Usage: /addadmin <user_id>")

@dp.message_handler(commands=["removeadmin"])
async def remove_admin(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    try:
        uid = int(m.get_args())
        if uid in data["admins"]:
            data["admins"].remove(uid)
            save_data()
            await m.reply(f"✅ Removed {uid} from admins.")
        else:
            await m.reply("⚠️ Not admin.")
    except:
        await m.reply("❌ Usage: /removeadmin <user_id>")

@dp.message_handler(commands=["showadmin"])
async def show_admins(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    admins = "\n".join(str(a) for a in data["admins"])
    await m.reply(f"👮 Admins:\n{admins}")

# ================= OWNER COMMANDS =================
@dp.message_handler(commands=["users"])
async def list_users(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    users = "\n".join(data["users"].keys())
    await m.reply(f"👤 Users:\n{users}")

@dp.message_handler(commands=["stats"])
async def stats(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    total_users = len(data["users"])
    total_admins = len(data["admins"])
    await m.reply(f"📊 Stats:\n👤 Users: {total_users}\n👮 Admins: {total_admins}")

@dp.message_handler(commands=["restart"])
async def restart(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    await m.reply("♻️ Restarting...")
    os.execv(sys.executable, ["python3"] + sys.argv)

# ================= BROADCAST =================
@dp.message_handler(commands=["broadcast"])
async def broadcast(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message:
        return await m.reply("❌ Reply to a message to broadcast.")
    success, fail = 0, 0
    for uid in list(data["users"].keys()):
        try:
            await m.reply_to_message.copy_to(int(uid))
            success += 1
        except:
            fail += 1
    await m.reply(f"📢 Broadcast done.\n✅ Success: {success}\n❌ Fail: {fail}")

@dp.message_handler(commands=["dbroadcast"])
async def dbroadcast(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message:
        return await m.reply("❌ Reply to a message to dbroadcast.")
    try:
        secs = int(m.get_args())
    except:
        return await m.reply("❌ Usage: /dbroadcast <seconds> (reply to msg)")
    success, fail = 0, 0
    for uid in list(data["users"].keys()):
        try:
            sent = await m.reply_to_message.copy_to(int(uid))
            await asyncio.sleep(secs)
            await bot.delete_message(int(uid), sent.message_id)
            success += 1
        except:
            fail += 1
    await m.reply(f"🕒 Timed broadcast done.\n✅ Success: {success}\n❌ Fail: {fail}")

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
