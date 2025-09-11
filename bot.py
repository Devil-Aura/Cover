import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InputMediaVideo

API_TOKEN = ""
OWNER_ID =   # 🔥 Replace with your Telegram ID

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CoverBot")

# Bot & Dispatcher
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# Simple DB
COVER_DB = {}   # {chat_id: file_id}
USERS = set()   # track chats for broadcast
ADMINS = {OWNER_ID}  # start with owner as admin


# ----------------- Helpers -----------------
def is_admin(uid: int):
    return uid in ADMINS or uid == OWNER_ID


async def save_cover(chat_id: int, file_id: str):
    COVER_DB[chat_id] = file_id


async def get_cover(chat_id: int):
    return COVER_DB.get(chat_id)


async def delete_cover(chat_id: int):
    if chat_id in COVER_DB:
        del COVER_DB[chat_id]


# ----------------- Commands -----------------
@dp.message_handler(commands=["start"])
async def start_cmd(m: types.Message):
    USERS.add(m.chat.id)
    await m.reply("👋 Hello! Send me an image to set as cover.\nSend a video and I’ll apply the cover instantly.")


@dp.message_handler(commands=["ping"])
async def ping_cmd(m: types.Message):
    start = asyncio.get_event_loop().time()
    msg = await m.reply("🏓 Pinging...")
    end = asyncio.get_event_loop().time()
    await msg.edit_text(f"✅ Pong! `{round((end - start) * 1000)} ms`")


@dp.message_handler(commands=["restart"])
async def restart_cmd(m: types.Message):
    if not is_admin(m.from_user.id):
        return await m.reply("⛔ Only admins can restart.")
    await m.reply("♻️ Restarting...")
    os.execv(sys.executable, ['python'] + sys.argv)


@dp.message_handler(commands=["show_cover"])
async def show_cover(m: types.Message):
    thumb = await get_cover(m.chat.id)
    if not thumb:
        await m.reply("⚠️ No cover set yet. Send me an image to save as cover.")
    else:
        await bot.send_photo(m.chat.id, thumb, caption="🖼️ Current saved cover:")


@dp.message_handler(commands=["delete_cover"])
async def delete_cover_cmd(m: types.Message):
    await delete_cover(m.chat.id)
    await m.reply("🗑️ Cover deleted successfully.")


@dp.message_handler(commands=["broadcast"])
async def broadcast_cmd(m: types.Message):
    if not is_admin(m.from_user.id):
        return await m.reply("⛔ Only admins can broadcast.")
    if not m.reply_to_message:
        return await m.reply("⚠️ Reply to a message to broadcast it.")
    for uid in USERS:
        try:
            await m.reply_to_message.copy_to(uid)
        except Exception as e:
            logger.error(f"Broadcast failed to {uid}: {e}")
    await m.reply("✅ Broadcast completed!")


@dp.message_handler(commands=["dbroadcast"])
async def dbroadcast_cmd(m: types.Message):
    if not is_admin(m.from_user.id):
        return await m.reply("⛔ Only admins can use dbroadcast.")
    if not m.reply_to_message:
        return await m.reply("⚠️ Reply to a message to broadcast it.\nUsage: /dbroadcast 30 (auto delete in 30s)")
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await m.reply("⚠️ Usage: /dbroadcast <seconds>")
    delay = int(args[1])

    for uid in USERS:
        try:
            sent = await m.reply_to_message.copy_to(uid)
            await asyncio.sleep(0.5)
            asyncio.create_task(auto_delete(uid, sent.message_id, delay))
        except Exception as e:
            logger.error(f"DBroadcast failed to {uid}: {e}")
    await m.reply(f"✅ Delayed broadcast sent! Will auto-delete in {delay}s.")


async def auto_delete(chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception:
        pass


# ----------------- Admin Commands -----------------
@dp.message_handler(commands=["addadmin"])
async def add_admin(m: types.Message):
    if m.from_user.id != OWNER_ID:
        return await m.reply("⛔ Only owner can add admins.")
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await m.reply("⚠️ Usage: /addadmin <user_id>")
    uid = int(args[1])
    ADMINS.add(uid)
    await m.reply(f"✅ User `{uid}` added as admin.")


@dp.message_handler(commands=["removeadmin"])
async def remove_admin(m: types.Message):
    if m.from_user.id != OWNER_ID:
        return await m.reply("⛔ Only owner can remove admins.")
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await m.reply("⚠️ Usage: /removeadmin <user_id>")
    uid = int(args[1])
    if uid in ADMINS:
        ADMINS.remove(uid)
        await m.reply(f"✅ User `{uid}` removed from admins.")
    else:
        await m.reply("⚠️ That user is not an admin.")


@dp.message_handler(commands=["showadmins"])
async def show_admins(m: types.Message):
    admins = list(ADMINS) + [OWNER_ID]
    text = "👑 <b>Admins:</b>\n" + "\n".join([f"• <code>{i}</code>" for i in admins])
    await m.reply(text)


# ----------------- Handlers -----------------
@dp.message_handler(content_types=["photo"])
async def on_photo(m: types.Message):
    file_id = m.photo[-1].file_id
    await save_cover(m.chat.id, file_id)
    await m.reply("✅ Cover thumbnail saved successfully!")


@dp.message_handler(content_types=["video"])
async def on_video(m: types.Message):
    thumb_id = await get_cover(m.chat.id)
    caption = m.caption or ""
    if is_admin(m.from_user.id):
        caption = f"<b>{caption}</b>" if caption else "<b>Video</b>"
    try:
        copied = await m.copy_to(m.chat.id, caption=caption)
        if thumb_id:
            await bot.edit_message_media(
                chat_id=m.chat.id,
                message_id=copied.message_id,
                media=InputMediaVideo(
                    media=m.video.file_id,
                    caption=caption,
                    thumb=thumb_id
                )
            )
    except Exception as e:
        logger.error(f"Instant Cover Error: {e}")
        await m.reply("⚠️ Failed to apply cover, but video was sent.")


# ----------------- Run -----------------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
