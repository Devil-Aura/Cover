#!/usr/bin/env python3
# bot.py - Aiogram v2.25.1
import os
import sys
import json
import time
import logging
import asyncio
import html
from typing import Dict, List, Tuple, Optional

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", ""))
DATA_FILE = "bot_data.json"
THUMBS_DIR = "thumbs"  # local storage for thumbnails

# ---------------- INIT ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CoverBot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

os.makedirs(THUMBS_DIR, exist_ok=True)

# ---------------- DATA ----------------
# data structure:
# {
#   "users": { "<user_id>": {"has_seen": true, "thumb_file": "thumbs/123.jpg" or None} },
#   "admins": [owner_id, ...]
# }
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"users": {}, "admins": [OWNER_ID]}, f, indent=2)

def load_data() -> Dict:
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(d: Dict):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

data = load_data()

def ensure_user(uid: int):
    s = str(uid)
    if s not in data["users"]:
        data["users"][s] = {"has_seen": True, "thumb_file": None}
        save_data(data)

def set_thumb_file(uid: int, local_path: str):
    ensure_user(uid)
    data["users"][str(uid)]["thumb_file"] = local_path
    save_data(data)

def get_thumb_file(uid: int) -> Optional[str]:
    return data["users"].get(str(uid), {}).get("thumb_file")

def remove_thumb(uid: int):
    p = get_thumb_file(uid)
    if p and os.path.exists(p):
        try:
            os.remove(p)
        except:
            pass
    ensure_user(uid)
    data["users"][str(uid)]["thumb_file"] = None
    save_data(data)

def is_owner(uid: int) -> bool:
    return uid == OWNER_ID

def is_admin(uid: int) -> bool:
    return uid in data.get("admins", [])

# ---------------- UTIL ----------------
def html_bold_escape(text: str) -> str:
    return f"<b>{html.escape(text)}</b>" if text else None

async def safe_copy_message(to_chat_id: int, from_chat_id: int, message_id: int) -> Optional[types.Message]:
    try:
        return await bot.copy_message(chat_id=to_chat_id, from_chat_id=from_chat_id, message_id=message_id)
    except Exception as e:
        logger.debug(f"copy_message failed to {to_chat_id}: {e}")
        return None

# ---------------- COMMANDS ----------------
@dp.message_handler(commands=["start"])
async def cmd_start(m: types.Message):
    ensure_user(m.from_user.id)
    text = (
        f"👋 Hi {html.escape(m.from_user.first_name or m.from_user.username or '')}!\n\n"
        "🎬 <b>Video Cover/Thumbnail Bot</b>\n\n"
        "• Send a photo — it will be saved automatically as your thumbnail.\n"
        "• Send a video — I'll re-upload it with your saved thumbnail applied.\n\n"
        "Commands:\n"
        "/show_cover - Show your saved cover\n"
        "/delete_cover - Delete your saved cover\n"
        "/ping - Check bot status\n\n"
        "🔗 Powered by @World_Fastest_Bots"
    )
    await m.reply(text, parse_mode="HTML")

@dp.message_handler(commands=["ping"])
async def cmd_ping(m: types.Message):
    t0 = time.time()
    tmp = await m.reply("🏓 Ping...")
    t1 = time.time()
    ms = int((t1 - t0) * 1000)
    await tmp.edit_text(f"🏓 Pong! `{ms} ms`")

# ---------------- THUMBNAIL: auto-save photo ----------------
@dp.message_handler(content_types=["photo"])
async def on_photo(m: types.Message):
    # Save highest-quality photo locally
    uid = m.from_user.id
    ensure_user(uid)
    file_name = f"{THUMBS_DIR}/{uid}.jpg"
    try:
        await m.photo[-1].download(destination_file=file_name)
        set_thumb_file(uid, file_name)
        # short confirmation
        await m.reply("✅ Thumbnail saved and will be applied to your future videos.")
    except Exception as e:
        logger.exception("Failed to save thumbnail: %s", e)
        await m.reply("⚠️ Failed to save thumbnail.")

@dp.message_handler(commands=["show_cover"])
async def cmd_show_cover(m: types.Message):
    ensure_user(m.from_user.id)
    p = get_thumb_file(m.from_user.id)
    if not p:
        return await m.reply("❌ You don't have a saved cover. Send a photo to save one.")
    try:
        await m.reply_photo(photo=open(p, "rb"), caption="🖼️ Your saved cover")
    except Exception:
        # Fallback: maybe file_id was stored (older), try sending by file_id
        try:
            await m.reply_photo(p, caption="🖼️ Your saved cover")
        except Exception as e:
            logger.exception("show_cover error: %s", e)
            await m.reply("⚠️ Couldn't show cover.")

@dp.message_handler(commands=["delete_cover", "deletethumb", "deletethumb"])
async def cmd_delete_cover(m: types.Message):
    ensure_user(m.from_user.id)
    remove_thumb(m.from_user.id)
    await m.reply("🗑️ Your cover has been deleted.")

# ---------------- VIDEO: reupload with thumb ----------------
@dp.message_handler(content_types=["video"])
async def on_video(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    thumb_path = get_thumb_file(uid)  # local path or None

    # prepare caption
    orig_caption = m.caption or ""
    if is_owner(uid) or is_admin(uid):
        caption = html_bold_escape(orig_caption) if orig_caption else None
        parse_mode = "HTML"
    else:
        caption = orig_caption if orig_caption else None
        parse_mode = None

    # Download video to a temp file so Telegram re-uploads it (forces applying thumb)
    tmp_video = f"temp_vid_{m.message_id}_{uid}.mp4"
    try:
        await m.video.download(destination_file=tmp_video)
    except Exception as e:
        logger.exception("Failed to download video: %s", e)
        return await m.reply("⚠️ Failed to download video to apply thumbnail.")

    # Send video by re-upload with thumb (if exists)
    try:
        if thumb_path and os.path.exists(thumb_path):
            # open files and send
            with open(tmp_video, "rb") as vf, open(thumb_path, "rb") as tf:
                await bot.send_video(chat_id=m.chat.id,
                                     video=vf,
                                     caption=caption,
                                     parse_mode=parse_mode,
                                     thumb=tf,
                                     supports_streaming=True)
        else:
            with open(tmp_video, "rb") as vf:
                await bot.send_video(chat_id=m.chat.id,
                                     video=vf,
                                     caption=caption,
                                     parse_mode=parse_mode,
                                     supports_streaming=True)
        # Remove temp file
        try:
            os.remove(tmp_video)
        except:
            pass
    except Exception as e:
        logger.exception("Error re-sending video with thumb: %s", e)
        # cleanup
        try:
            os.remove(tmp_video)
        except:
            pass
        await m.reply(f"⚠️ Error sending video with thumbnail: {e}")

# ---------------- DOCUMENT / AUDIO: optionally apply thumb if user wants ----------------
@dp.message_handler(content_types=["document"])
async def on_document(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    thumb_path = get_thumb_file(uid)

    orig_caption = m.caption or ""
    if is_owner(uid) or is_admin(uid):
        caption = html_bold_escape(orig_caption) if orig_caption else None
        parse_mode = "HTML"
    else:
        caption = orig_caption if orig_caption else None
        parse_mode = None

    # We will just copy the document file_id (no re-upload) — can't attach thumb to existing file_id reliably.
    # If you'd like to re-upload with thumb, we could download and re-upload similar to video (but may be heavy).
    try:
        if thumb_path and os.path.exists(thumb_path):
            # re-upload document with thumb by downloading and reuploading
            tmp_doc = f"temp_doc_{m.message_id}_{uid}"
            try:
                await m.document.download(destination_file=tmp_doc)
                with open(tmp_doc, "rb") as df, open(thumb_path, "rb") as tf:
                    await bot.send_document(chat_id=m.chat.id, document=df, caption=caption, parse_mode=parse_mode, thumb=tf)
                try:
                    os.remove(tmp_doc)
                except:
                    pass
            except Exception as e:
                logger.exception("Reupload document failed: %s", e)
                # fallback to copy
                await m.document.copy_to(m.chat.id)
        else:
            # simple copy to re-send (preserves original file)
            await m.document.copy_to(m.chat.id)
    except Exception as e:
        logger.exception("Error handling document: %s", e)
        await m.reply(f"⚠️ Error processing document: {e}")

@dp.message_handler(content_types=["audio"])
async def on_audio(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    thumb_path = get_thumb_file(uid)

    orig_caption = m.caption or ""
    if is_owner(uid) or is_admin(uid):
        caption = html_bold_escape(orig_caption) if orig_caption else None
        parse_mode = "HTML"
    else:
        caption = orig_caption if orig_caption else None
        parse_mode = None

    try:
        if thumb_path and os.path.exists(thumb_path):
            tmp_audio = f"temp_audio_{m.message_id}_{uid}"
            try:
                await m.audio.download(destination_file=tmp_audio)
                with open(tmp_audio, "rb") as af, open(thumb_path, "rb") as tf:
                    await bot.send_audio(chat_id=m.chat.id, audio=af, caption=caption, parse_mode=parse_mode, thumb=tf)
                try:
                    os.remove(tmp_audio)
                except:
                    pass
            except Exception as e:
                logger.exception("Reupload audio failed: %s", e)
                await m.audio.copy_to(m.chat.id)
        else:
            await m.audio.copy_to(m.chat.id)
    except Exception as e:
        logger.exception("Error handling audio: %s", e)
        await m.reply(f"⚠️ Error processing audio: {e}")

# ---------------- ADMIN MANAGEMENT ----------------
@dp.message_handler(commands=["addadmin"])
async def cmd_addadmin(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    arg = m.get_args().strip()
    if not arg:
        return await m.reply("Usage: /addadmin <user_id>")
    try:
        uid = int(arg)
        if uid in data.get("admins", []):
            return await m.reply("⚠️ Already an admin.")
        data.setdefault("admins", []).append(uid)
        save_data(data)
        await m.reply(f"✅ Added admin: <code>{uid}</code>", parse_mode="HTML")
    except Exception:
        await m.reply("❌ Invalid user id.")

@dp.message_handler(commands=["removeadmin"])
async def cmd_removeadmin(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    arg = m.get_args().strip()
    if not arg:
        return await m.reply("Usage: /removeadmin <user_id>")
    try:
        uid = int(arg)
        if uid == OWNER_ID:
            return await m.reply("⚠️ Cannot remove owner.")
        if uid not in data.get("admins", []):
            return await m.reply("⚠️ Not an admin.")
        data["admins"].remove(uid)
        save_data(data)
        await m.reply(f"🗑️ Removed admin: <code>{uid}</code>", parse_mode="HTML")
    except Exception:
        await m.reply("❌ Invalid user id.")

@dp.message_handler(commands=["showadmin"])
async def cmd_showadmin(m: types.Message):
    if not (is_owner(m.from_user.id) or is_admin(m.from_user.id)):
        return
    admins = data.get("admins", [])
    text = "👮 Admins:\n" + "\n".join(f"• <code>{a}</code>" for a in admins)
    await m.reply(text, parse_mode="HTML")

# ---------------- OWNER FUNCTIONS ----------------
@dp.message_handler(commands=["users"])
async def cmd_users(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    await m.reply(f"👥 Total users stored: {len(data['users'])}")

@dp.message_handler(commands=["stats"])
async def cmd_stats(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    thumbs_count = sum(1 for v in data["users"].values() if v.get("thumb_file"))
    await m.reply(f"📊 Stats:\n• Users: {len(data['users'])}\n• Admins: {len(data.get('admins', []))}\n• Thumbnails saved: {thumbs_count}")

@dp.message_handler(commands=["restart"])
async def cmd_restart(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    await m.reply("♻️ Restarting...")
    save_data(data)
    os.execv(sys.executable, [sys.executable] + sys.argv)

# ---------------- BROADCAST / DBROADCAST ----------------
@dp.message_handler(commands=["broadcast"])
async def cmd_broadcast(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message:
        return await m.reply("❌ Reply to a message to broadcast it (text/photo/video/doc/etc).")
    sent = 0
    failed = 0
    for uid_str in list(data["users"].keys()):
        uid = int(uid_str)
        try:
            await safe_copy_message(uid, m.reply_to_message.chat.id, m.reply_to_message.message_id)
            sent += 1
            await asyncio.sleep(0.08)
        except Exception as e:
            logger.debug("broadcast fail %s: %s", uid, e)
            failed += 1
    await m.reply(f"📢 Broadcast finished. Sent: {sent}, Failed: {failed}")

@dp.message_handler(commands=["dbroadcast"])
async def cmd_dbroadcast(m: types.Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message:
        return await m.reply("❌ Reply to a message to dbroadcast it (text/photo/video/doc/etc).")
    args = m.get_args().strip()
    if not args:
        return await m.reply("❌ Usage: /dbroadcast <seconds>  (reply to a message)")
    try:
        seconds = int(args)
        if seconds <= 0:
            raise ValueError
    except:
        return await m.reply("❌ Invalid seconds. Example: /dbroadcast 30 (reply to a message)")

    records: List[Tuple[int,int]] = []
    for uid_str in list(data["users"].keys()):
        uid = int(uid_str)
        try:
            copied = await safe_copy_message(uid, m.reply_to_message.chat.id, m.reply_to_message.message_id)
            if copied:
                records.append((uid, copied.message_id))
            await asyncio.sleep(0.08)
        except Exception as e:
            logger.debug("dbroadcast fail %s: %s", uid, e)
            continue

    await m.reply(f"✅ Timed broadcast sent to {len(records)} users. Will delete in {seconds}s.")

    async def delete_after(recs: List[Tuple[int,int]], delay: int):
        await asyncio.sleep(delay)
        for c, mid in recs:
            try:
                await bot.delete_message(chat_id=c, message_id=mid)
            except Exception:
                pass

    asyncio.create_task(delete_after(records, seconds))

# ---------------- GLOBAL ERROR HANDLER ----------------
@dp.errors_handler()
async def on_error(update, exception):
    logger.exception("Unhandled exception: %s", exception)
    return True

# ---------------- RUN ----------------
if __name__ == "__main__":
    logger.info("Starting CoverBot (Aiogram v2.25.1)")
    executor.start_polling(dp, skip_updates=True)
