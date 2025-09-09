import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import ChatAdminRequired, UserNotParticipant
import os
import sys

# ========================= CONFIG =========================
BOT_TOKEN = ""
OWNER_ID = 
FORCE_SUB_CHANNEL = -1002432405855   # your channel id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Memory storage (no DB)
user_covers = {}
admins = set()
users = set()


# ========================= HELPERS =========================
async def is_user_joined(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except UserNotParticipant:
        return False
    except ChatAdminRequired:
        return True
    except Exception:
        return False


def bold_if_admin(user_id: int, text: str) -> str:
    if user_id == OWNER_ID or user_id in admins:
        return f"<b>{text}</b>"
    return text


# ========================= COMMANDS =========================
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    users.add(message.from_user.id)
    if not await is_user_joined(message.from_user.id):
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/c/{str(FORCE_SUB_CHANNEL)[4:]}")
        )
        return await message.reply(
            "⚠️ You must join our channel to use this bot.",
            reply_markup=kb
        )

    text = (
        "👋 Welcome to <b>Video Cover/Thumbnail Bot</b>\n\n"
        "✨ Send me a <b>photo</b> to save as your thumbnail.\n"
        "🎬 Then send a <b>video</b>, I’ll add the cover automatically.\n\n"
        "⚡ Powered By @World_Fastest_Bots"
    )
    await message.reply(text, parse_mode="HTML")


@dp.message_handler(commands=["show_cover"])
async def show_cover(message: types.Message):
    uid = message.from_user.id
    if uid not in user_covers:
        return await message.reply("❌ No thumbnail saved.")
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("❌ Delete Thumbnail", callback_data="del_cover")
    )
    await message.reply_photo(user_covers[uid], caption="🎭 Your saved thumbnail:", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == "del_cover")
async def del_cover_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if uid in user_covers:
        del user_covers[uid]
        await callback.message.edit_caption("🗑️ Thumbnail deleted.")
    await callback.answer()


@dp.message_handler(commands=["addadmin"])
async def add_admin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.get_args())
        admins.add(uid)
        await message.reply(f"✅ Added admin: <code>{uid}</code>", parse_mode="HTML")
    except:
        await message.reply("❌ Usage: /addadmin user_id")


@dp.message_handler(commands=["removeadmin"])
async def remove_admin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.get_args())
        admins.discard(uid)
        await message.reply(f"❌ Removed admin: <code>{uid}</code>", parse_mode="HTML")
    except:
        await message.reply("❌ Usage: /removeadmin user_id")


@dp.message_handler(commands=["showadmin"])
async def show_admins(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    if not admins:
        return await message.reply("⚠️ No admins added.")
    text = "👮 Admins:\n" + "\n".join([f"• <code>{a}</code>" for a in admins])
    await message.reply(text, parse_mode="HTML")


@dp.message_handler(commands=["users"])
async def users_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply(f"👥 Total users: {len(users)}")


@dp.message_handler(commands=["stats"])
async def stats_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    text = (
        f"📊 Stats:\n"
        f"👥 Users: {len(users)}\n"
        f"👮 Admins: {len(admins)}\n"
    )
    await message.reply(text)


@dp.message_handler(commands=["restart"])
async def restart_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply("♻️ Restarting...")
    os.execv(sys.executable, [sys.executable] + sys.argv)


@dp.message_handler(commands=["dbroadcast"])
async def dbroadcast_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        args = message.get_args().split(maxsplit=1)
        seconds = int(args[0])
        text = args[1]
    except:
        return await message.reply("❌ Usage: /dbroadcast <seconds> <message>")

    sent = []
    for uid in users:
        try:
            m = await bot.send_message(uid, text)
            sent.append((uid, m.message_id))
        except:
            pass
    await message.reply(f"✅ Broadcast sent to {len(sent)} users, will delete in {seconds}s")

    await asyncio.sleep(seconds)
    for uid, mid in sent:
        try:
            await bot.delete_message(uid, mid)
        except:
            pass


# ========================= HANDLERS =========================
@dp.message_handler(content_types=["photo"])
async def save_cover(message: types.Message):
    user_covers[message.from_user.id] = message.photo[-1].file_id
    await message.reply("✅ Thumbnail saved!")


@dp.message_handler(content_types=["video"])
async def handle_video(message: types.Message):
    uid = message.from_user.id
    if not await is_user_joined(uid):
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/c/{str(FORCE_SUB_CHANNEL)[4:]}")
        )
        return await message.reply("⚠️ You must join our channel to use this bot.", reply_markup=kb)

    caption = bold_if_admin(uid, message.caption or "")
    try:
        if uid in user_covers:
            await bot.send_video(
                chat_id=message.chat.id,
                video=message.video.file_id,
                caption=caption,
                thumb=user_covers[uid],
                parse_mode="HTML"
            )
        else:
            await bot.send_video(
                chat_id=message.chat.id,
                video=message.video.file_id,
                caption=caption,
                parse_mode="HTML"
            )
    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")


# ========================= START BOT =========================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
