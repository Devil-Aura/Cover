#!/usr/bin/env python3
import os
import sys
import time
import asyncio
import logging
from typing import Dict, Set, Tuple, List

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.utils.exceptions import (
    ChatNotFound, UserNotParticipant, BotBlocked, RetryAfter, TelegramAPIError
)

# ----------------- CONFIG -----------------
# Prefer environment variables; fallback to hardcoded values if not provided.
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", ""))
# Force-sub channel (use channel username link below). If you have username, change JOIN_URL.
FORCE_SUB_CHANNEL = int(os.getenv("FORCE_SUB_CHANNEL", "-1002432405855"))
JOIN_URL = os.getenv("JOIN_URL", "https://t.me/World_Fastest_Bots")

# ----------------- INIT -------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("thumbbot")

bot = Bot(token=BOT_TOKEN, parse_mode=None)  # we'll set parse_mode per-send
dp = Dispatcher(bot)

# ----------------- MEMORY DB -----------------
admins: List[int] = [OWNER_ID]               # owner is admin by default
user_thumbs: Dict[int, str] = {}             # user_id -> thumb file_id
known_chats: Set[int] = set()                # chats for broadcast
known_users: Set[int] = set()                # unique users seen/interacted


# ----------------- HELPERS -----------------
async def check_force_sub(user_id: int) -> bool:
    """Return True if user is member/creator/admin of FORCE_SUB_CHANNEL."""
    try:
        member = await bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except UserNotParticipant:
        return False
    except ChatNotFound:
        logger.error("Force-sub channel not found (invalid ID).")
        return False
    except TelegramAPIError as e:
        # Could be Bot was kicked or something else; log and return False
        logger.warning(f"check_force_sub error: {e}")
        return False


def is_admin(user_id: int) -> bool:
    return user_id in admins


def owner_only(func):
    async def wrapper(message: types.Message):
        if message.from_user.id != OWNER_ID:
            await message.reply("⛔ This command is owner-only.")
            return
        return await func(message)
    return wrapper


# ----------------- START -----------------
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    # Force sub check
    if not await check_force_sub(uid):
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("🚀 Join Channel", url=JOIN_URL)
        )
        await message.reply("⚠️ You must join our channel to use this bot!", reply_markup=kb)
        return

    # register user & chat
    known_users.add(uid)
    known_chats.add(message.chat.id)

    start_text = (
        f"👋 Hey <b>{message.from_user.first_name}</b>!\n\n"
        "✨ I change video thumbnails (covers) for you — automatically.\n\n"
        "📸 Send any image and it will be saved as your thumbnail.\n"
        "🎞️ Then send a video (or document) and I'll re-upload it with your thumbnail.\n\n"
        "⚡ Fast • Simple • Powerful\n\n"
        "🔗 Powered By @World_Fastest_Bots"
    )
    await message.reply(start_text, parse_mode="HTML")


# ----------------- THUMBNAIL HANDLERS -----------------
@dp.message_handler(content_types=["photo"])
async def handle_photo(message: types.Message):
    """Auto-save the last photo as user's thumbnail (file_id)."""
    uid = message.from_user.id
    # Save file_id (highest quality)
    file_id = message.photo[-1].file_id
    user_thumbs[uid] = file_id

    # register user/chat
    known_users.add(uid)
    known_chats.add(message.chat.id)

    await message.reply("✅ Thumbnail saved automatically! Now send a video.")


@dp.message_handler(commands=["show_cover"])
async def cmd_show_cover(message: types.Message):
    uid = message.from_user.id
    if uid not in user_thumbs:
        return await message.reply("❌ You don't have a saved thumbnail. Send a photo to save one.")

    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Delete Thumbnail", callback_data="del_thumb"))
    await message.reply_photo(user_thumbs[uid], caption="📌 Your saved thumbnail:", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == "del_thumb")
async def cb_delete_thumb(callback_query: types.CallbackQuery):
    uid = callback_query.from_user.id
    if uid in user_thumbs:
        user_thumbs.pop(uid, None)
        await callback_query.message.edit_caption("🗑️ Thumbnail deleted.")
        await callback_query.answer("Deleted.")
    else:
        await callback_query.answer("❌ No thumbnail found.", show_alert=True)


@dp.message_handler(commands=["del_cover", "delthumb", "delthumbnail"])
async def cmd_del_cover(message: types.Message):
    uid = message.from_user.id
    if uid in user_thumbs:
        user_thumbs.pop(uid, None)
        await message.reply("🗑️ Thumbnail deleted.")
    else:
        await message.reply("❌ No thumbnail to delete.")


# ----------------- MEDIA HANDLING -----------------
@dp.message_handler(content_types=["video", "document"])
async def handle_media(message: types.Message):
    """Re-upload video/document with user's thumbnail (thumb param)."""
    uid = message.from_user.id

    # Force-sub check
    if not await check_force_sub(uid):
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 Join Channel", url=JOIN_URL))
        await message.reply("⚠️ You must join our channel to use this bot!", reply_markup=kb)
        return

    known_users.add(uid)
    known_chats.add(message.chat.id)

    thumb = user_thumbs.get(uid)  # file_id or None
    orig_caption = message.caption or ""

    # For admins/owner: bold the caption; for others: keep exactly as sent (no parse)
    if is_admin(uid) and orig_caption:
        # escape and wrap in bold with HTML to avoid markup injection
        import html as _html
        caps = _html.escape(orig_caption)
        caption_to_send = f"<b>{caps}</b>"
        parse_mode = "HTML"
    else:
        caption_to_send = orig_caption if orig_caption else None
        parse_mode = None

    # Choose function based on type
    try:
        if message.video:
            await bot.send_video(
                chat_id=message.chat.id,
                video=message.video.file_id,
                caption=caption_to_send,
                parse_mode=parse_mode,
                thumb=thumb,
                supports_streaming=True
            )
        else:  # document
            # send_document accepts thumb param too
            await bot.send_document(
                chat_id=message.chat.id,
                document=message.document.file_id,
                caption=caption_to_send,
                parse_mode=parse_mode,
                thumb=thumb
            )
    except RetryAfter as e:
        logger.warning(f"Flood: RetryAfter {e.timeout}s")
        await asyncio.sleep(e.timeout)
        # a single retry
        try:
            if message.video:
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=message.video.file_id,
                    caption=caption_to_send,
                    parse_mode=parse_mode,
                    thumb=thumb,
                    supports_streaming=True
                )
            else:
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=message.document.file_id,
                    caption=caption_to_send,
                    parse_mode=parse_mode,
                    thumb=thumb
                )
        except Exception as ex:
            logger.exception("send after RetryAfter failed: %s", ex)
            await message.reply(f"⚠️ Error sending media after retry: {ex}")
    except TelegramAPIError as e:
        logger.exception("Error sending media: %s", e)
        await message.reply(f"⚠️ Error: {e}")


# ----------------- SIMPLE COMMANDS -----------------
@dp.message_handler(commands=["ping"])
async def cmd_ping(message: types.Message):
    t0 = time.time()
    m = await message.reply("🏓 Ping...")
    t1 = time.time()
    ms = int((t1 - t0) * 1000)
    await m.edit_text(f"🏓 Pong! `{ms} ms`")


# ----------------- ADMIN MANAGEMENT -----------------
@dp.message_handler(commands=["addadmin"])
async def cmd_addadmin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Only owner can add admins.")
    arg = message.get_args().strip()
    if not arg:
        return await message.reply("Usage: /addadmin <user_id>")
    try:
        uid = int(arg)
        if uid in admins:
            return await message.reply("⚠️ User already an admin.")
        admins.append(uid)
        await message.reply(f"✅ Added {uid} as admin.")
    except:
        await message.reply("❌ Invalid user id.")


@dp.message_handler(commands=["removeadmin"])
async def cmd_removeadmin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Only owner can remove admins.")
    arg = message.get_args().strip()
    if not arg:
        return await message.reply("Usage: /removeadmin <user_id>")
    try:
        uid = int(arg)
        if uid == OWNER_ID:
            return await message.reply("⚠️ Cannot remove owner.")
        if uid not in admins:
            return await message.reply("⚠️ This user is not an admin.")
        admins.remove(uid)
        await message.reply(f"🗑️ Removed {uid} from admins.")
    except:
        await message.reply("❌ Invalid user id.")


@dp.message_handler(commands=["showadmin"])
async def cmd_showadmin(message: types.Message):
    # allow owner and admins to view admin list
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ You are not an admin.")
    text = "👑 Admins:\n" + "\n".join(str(x) for x in admins)
    await message.reply(text)


# ----------------- OWNER-ONLY EXTRA -----------------
@dp.message_handler(commands=["users"])
async def cmd_users(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Owner only.")
    await message.reply(f"👥 Total known users: {len(known_users)}")


@dp.message_handler(commands=["stats"])
async def cmd_stats(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Owner only.")
    txt = (
        "📊 Bot Stats\n\n"
        f"👥 Known users: {len(known_users)}\n"
        f"👑 Admins: {len(admins)}\n"
        f"💬 Known chats: {len(known_chats)}\n"
        f"🖼️ Thumbnails saved: {len(user_thumbs)}"
    )
    await message.reply(txt)


@dp.message_handler(commands=["restart"])
async def cmd_restart(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Owner only.")
    await message.reply("♻️ Restarting...")
    await bot.close()
    # restart process
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ----------------- BROADCASTS -----------------
@dp.message_handler(commands=["broadcast"])
async def cmd_broadcast(message: types.Message):
    """Owner-only plain broadcast (no delete). Reply to a message to broadcast."""
    if message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Owner only.")
    if not message.reply_to_message:
        return await message.reply("⚠️ Reply to a message to broadcast.")
    sent = 0
    failed = 0
    for chat_id in list(known_chats):
        try:
            # copy_message preserves formatting & avoids reupload
            await bot.copy_message(chat_id=chat_id, from_chat_id=message.reply_to_message.chat.id,
                                   message_id=message.reply_to_message.message_id)
            sent += 1
            await asyncio.sleep(0.08)  # small delay to avoid flood
        except BotBlocked:
            failed += 1
        except ChatNotFound:
            failed += 1
        except RetryAfter as e:
            logger.warning("Flood wait in broadcast: sleeping %s", e.timeout)
            await asyncio.sleep(e.timeout)
        except Exception as e:
            logger.exception("Broadcast error: %s", e)
            failed += 1
    await message.reply(f"📢 Broadcast finished. Sent: {sent}, Failed: {failed}")


@dp.message_handler(commands=["dbroadcast"])
async def cmd_dbroadcast(message: types.Message):
    """
    Owner-only timed broadcast. Usage: reply to message and send: /dbroadcast <seconds>
    The copied messages will be auto-deleted after <seconds>.
    """
    if message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Owner only.")
    if not message.reply_to_message:
        return await message.reply("⚠️ Reply to a message to broadcast.")
    arg = message.get_args().strip()
    if not arg:
        return await message.reply("⚠️ Usage: /dbroadcast <seconds> (reply to a message)")
    try:
        seconds = int(arg)
        if seconds <= 0:
            return await message.reply("⚠️ Time must be positive integer seconds.")
    except:
        return await message.reply("❌ Invalid time. Use seconds (e.g. 30).")

    sent_records: List[Tuple[int, int]] = []
    for chat_id in list(known_chats):
        try:
            sent_msg = await bot.copy_message(chat_id=chat_id, from_chat_id=message.reply_to_message.chat.id,
                                              message_id=message.reply_to_message.message_id)
            sent_records.append((chat_id, sent_msg.message_id))
            await asyncio.sleep(0.08)
        except BotBlocked:
            continue
        except ChatNotFound:
            continue
        except RetryAfter as e:
            logger.warning("Flood wait in dbroadcast: sleeping %s", e.timeout)
            await asyncio.sleep(e.timeout)
        except Exception as e:
            logger.exception("dbroadcast send error: %s", e)
            continue

    await message.reply(f"✅ Timed broadcast sent to {len(sent_records)} chats. Will delete in {seconds}s.")

    # schedule deletions
    async def delete_after(records: List[Tuple[int, int]], delay: int):
        await asyncio.sleep(delay)
        for c_id, m_id in records:
            try:
                await bot.delete_message(chat_id=c_id, message_id=m_id)
            except Exception:
                pass

    asyncio.create_task(delete_after(sent_records, seconds))


# ----------------- ERROR HANDLER -----------------
@dp.errors_handler()
async def global_error_handler(update, exception):
    logger.exception("Global handler caught: %s", exception)
    return True


# ----------------- START BOT -----------------
if __name__ == "__main__":
    logger.info("Starting bot...")
    executor.start_polling(dp, skip_updates=True)
