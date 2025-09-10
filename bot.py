import os
import json
import logging
import asyncio
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import Message, ChatMember
from aiogram.utils.exceptions import ChatAdminRequired

# ===================== CONFIG =====================
BOT_TOKEN = ""
OWNER_ID = 
FORCE_SUB_CHANNEL = -1002432405855
DATA_FILE = "bot_data.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ===================== DATA STORAGE =====================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "admins": [OWNER_ID]}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# ===================== HELPERS =====================
async def check_force_sub(user_id):
    try:
        member = await bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        if member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
            return True
        return False
    except ChatAdminRequired:
        return True  # Bot is not admin, skip check
    except Exception as e:
        logger.error(f"ForceSub error: {e}")
        return True

def is_admin(user_id):
    return user_id in data.get("admins", [])

# ===================== START =====================
@dp.message_handler(commands=["start"])
async def start_cmd(message: Message):
    user_id = message.from_user.id
    if not await check_force_sub(user_id):
        btn = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("📢 Join Channel", url="https://t.me/World_Fastest_Bots"),
            types.InlineKeyboardButton("✅ Joined", callback_data="checksub")
        )
        return await message.answer("⚠️ You must join our channel to use this bot.", reply_markup=btn)

    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {"thumbnail": None}
        save_data(data)

    text = (
        "🎬 **Welcome to Video Thumbnail Changer Bot!**\n\n"
        "📌 Send a **video**, then send an **image** to set as its thumbnail.\n"
        "✨ If you send only an image, it will be saved as your default thumbnail.\n\n"
        "⚡ Powered by @World_Fastest_Bots"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == "checksub")
async def check_subscription(callback_query: types.CallbackQuery):
    if await check_force_sub(callback_query.from_user.id):
        await callback_query.message.edit_text("✅ You have access now. Send me a video to continue.")
    else:
        await callback_query.answer("❌ You are still not joined.", show_alert=True)

# ===================== THUMBNAIL =====================
@dp.message_handler(content_types=["photo"])
async def save_thumbnail(message: Message):
    user_id = str(message.from_user.id)
    file_id = message.photo[-1].file_id
    data["users"][user_id]["thumbnail"] = file_id
    save_data(data)
    await message.reply("✅ Thumbnail saved. Now send me a video.")

# ===================== VIDEO =====================
@dp.message_handler(content_types=["video"])
async def handle_video(message: Message):
    user_id = str(message.from_user.id)
    caption = message.caption or ""

    if is_admin(message.from_user.id):
        caption = f"<b>{caption}</b>" if caption else ""

    thumb = data["users"].get(user_id, {}).get("thumbnail")

    try:
        await bot.send_video(
            chat_id=message.chat.id,
            video=message.video.file_id,
            caption=caption,
            parse_mode="HTML",
            thumb=thumb
        )
    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")

# ===================== ADMIN COMMANDS =====================
@dp.message_handler(commands=["addadmin"])
async def add_admin(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.get_args())
        if uid not in data["admins"]:
            data["admins"].append(uid)
            save_data(data)
            await message.reply(f"✅ Added {uid} as admin.")
        else:
            await message.reply("⚠️ Already an admin.")
    except:
        await message.reply("❌ Usage: /addadmin user_id")

@dp.message_handler(commands=["removeadmin"])
async def remove_admin(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.get_args())
        if uid in data["admins"]:
            data["admins"].remove(uid)
            save_data(data)
            await message.reply(f"✅ Removed {uid} from admins.")
        else:
            await message.reply("⚠️ Not an admin.")
    except:
        await message.reply("❌ Usage: /removeadmin user_id")

@dp.message_handler(commands=["showadmin"])
async def show_admins(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    admins = "\n".join(str(a) for a in data["admins"])
    await message.reply(f"👮 Admins:\n{admins}")

# ===================== OWNER COMMANDS =====================
@dp.message_handler(commands=["users"])
async def list_users(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    users = "\n".join(data["users"].keys())
    await message.reply(f"👤 Users:\n{users}")

@dp.message_handler(commands=["stats"])
async def stats(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    total_users = len(data["users"])
    total_admins = len(data["admins"])
    await message.reply(f"📊 Stats:\n👤 Users: {total_users}\n👮 Admins: {total_admins}")

@dp.message_handler(commands=["restart"])
async def restart(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply("♻️ Restarting...")
    os.execv(sys.executable, ["python3"] + sys.argv)

@dp.message_handler(commands=["dbroadcast"])
async def dbroadcast(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    text = message.get_args()
    if not text:
        return await message.reply("❌ Usage: /dbroadcast <message>")

    success = 0
    fail = 0
    for uid in data["users"].keys():
        try:
            await bot.send_message(int(uid), text)
            success += 1
        except:
            fail += 1
    await message.reply(f"✅ Broadcast done.\nSuccess: {success}\nFail: {fail}")

# ===================== RUN =====================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
