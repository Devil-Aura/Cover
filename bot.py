import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.utils.exceptions import ChatAdminRequired, UserNotParticipantError

# ---------------- CONFIG ----------------
API_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", ""))
FORCE_SUB_CHANNEL = int(os.getenv("FORCE_SUB_CHANNEL", "-1002432405855"))

# Initialize
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# In-memory storage
user_thumbs = {}
admins = set([OWNER_ID])
users = set()

# ---------------- HELPERS ----------------
async def is_user_joined(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except UserNotParticipantError:
        return False
    except ChatAdminRequired:
        return True
    except Exception:
        return False

def is_admin(user_id: int) -> bool:
    return user_id in admins or user_id == OWNER_ID

# ---------------- COMMANDS ----------------
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    users.add(user_id)

    if not await is_user_joined(user_id):
        btn = InlineKeyboardMarkup().add(
            InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/c/{str(FORCE_SUB_CHANNEL)[4:]}")
        )
        return await message.reply("⚠️ You must join our channel to use this bot.", reply_markup=btn)

    await message.reply(
        f"👋 Hi {message.from_user.first_name}!\n\n"
        "🎬 **Video Cover/Thumbnail Bot**\n\n"
        "✨ Send me a photo → It will be saved as your thumbnail.\n"
        "🎥 Send me a video → I’ll apply your saved thumbnail.\n\n"
        "⚡ Commands:\n"
        "/show_cover - View your thumbnail\n"
        "/del_cover - Delete your thumbnail\n"
        "/ping - Check if bot is alive\n\n"
        "Powered By: @World_Fastest_Bots"
    )

@dp.message_handler(commands=["ping"])
async def ping_cmd(message: types.Message):
    await message.reply("✅ Pong! Bot is alive.")

@dp.message_handler(commands=["addadmin"])
async def add_admin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.get_args())
        admins.add(uid)
        await message.reply(f"✅ User `{uid}` added as admin.")
    except:
        await message.reply("⚠️ Usage: /addadmin <user_id>")

@dp.message_handler(commands=["removeadmin"])
async def remove_admin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.get_args())
        admins.discard(uid)
        await message.reply(f"❌ User `{uid}` removed from admins.")
    except:
        await message.reply("⚠️ Usage: /removeadmin <user_id>")

@dp.message_handler(commands=["showadmin"])
async def show_admin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    text = "👮 Admins:\n" + "\n".join([str(a) for a in admins])
    await message.reply(text)

@dp.message_handler(commands=["users"])
async def users_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply(f"👥 Total users: {len(users)}")

@dp.message_handler(commands=["stats"])
async def stats_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply(
        f"📊 Stats:\n"
        f"👥 Users: {len(users)}\n"
        f"👮 Admins: {len(admins)}"
    )

@dp.message_handler(commands=["restart"])
async def restart_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply("♻️ Restarting bot...")
    os.execl(sys.executable, sys.executable, *sys.argv)

@dp.message_handler(commands=["dbroadcast"])
async def dbroadcast_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    args = message.get_args().split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("⚠️ Usage: /dbroadcast <seconds> <message>")
    try:
        seconds = int(args[0])
        text = args[1]
    except:
        return await message.reply("⚠️ Invalid format. Example: /dbroadcast 30 Hello World")

    for uid in users:
        try:
            sent = await bot.send_message(uid, text)
            await asyncio.sleep(0.1)
            await asyncio.sleep(seconds)
            await bot.delete_message(uid, sent.message_id)
        except:
            continue
    await message.reply("✅ Timed broadcast sent.")

# ---------------- THUMBNAIL ----------------
@dp.message_handler(content_types=["photo"])
async def save_thumb(message: types.Message):
    user_id = message.from_user.id
    user_thumbs[user_id] = message.photo[-1].file_id
    await message.reply("✅ Thumbnail saved! Now send me a video.")

@dp.message_handler(commands=["show_cover"])
async def show_cover(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_thumbs:
        return await message.reply("❌ No thumbnail found.")
    btn = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Delete", callback_data="del_thumb"))
    await message.reply_photo(user_thumbs[user_id], caption="🎬 Your saved thumbnail.", reply_markup=btn)

@dp.callback_query_handler(lambda c: c.data == "del_thumb")
async def del_thumb_cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in user_thumbs:
        del user_thumbs[user_id]
        await callback.message.edit_caption("🗑️ Thumbnail deleted.")
    else:
        await callback.answer("❌ No thumbnail found.", show_alert=True)

@dp.message_handler(commands=["del_cover"])
async def del_cover(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_thumbs:
        del user_thumbs[user_id]
        await message.reply("🗑️ Thumbnail deleted.")
    else:
        await message.reply("❌ No thumbnail found.")

@dp.message_handler(content_types=["video"])
async def apply_thumb(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_thumbs:
        return await message.reply("⚠️ No thumbnail set. Send me a photo first.")

    caption = message.caption or ""
    if is_admin(user_id):
        caption = f"**{caption}**" if caption else ""

    await bot.send_video(
        chat_id=message.chat.id,
        video=message.video.file_id,
        caption=caption,
        thumb=user_thumbs[user_id]
    )

# ---------------- MAIN ----------------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
