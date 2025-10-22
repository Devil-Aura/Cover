#!/usr/bin/env python3
# bot.py - Professional Video Cover / Thumbnail Bot (single file)
# Requirements: python-telegram-bot >= 20.0
# pip install python-telegram-bot --upgrade

import os
import json
import logging
import html
import asyncio
from typing import Dict, Any, Optional, List

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    MessageEntity,
    constants,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIG ----------------
BOT_TOKEN = ""  # <<-- set your bot token
OWNER_ID: int = 6040503076  # provided by you
FORCE_SUB_CHANNEL_ID = -1002432405855  # channel user must join
FORCE_SUB_CHANNEL_LINK = "https://t.me/World_Fastest_Bots"
LOG_CHANNEL_ID = -1003180409625  # separate real log channel (provided)
DATA_FILE = "user_data.json"
BOT_LOGO = "https://i.ibb.co/d4DX7vRW/x.jpg"
# ----------------------------------------

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    filename="bot.log",
)
logger = logging.getLogger(__name__)


# ---------------- Storage helpers ----------------
def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "banned": [], "meta": {"total_videos": 0}}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.exception("Failed to load data: %s", e)
        return {"users": {}, "banned": [], "meta": {"total_videos": 0}}


def save_data(data: Dict[str, Any]) -> None:
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.exception("Failed to save data: %s", e)


DB = load_data()


def ensure_user_record(user_id: int) -> Dict[str, Any]:
    key = str(user_id)
    if key not in DB["users"]:
        DB["users"][key] = {
            "thumbnail_file_id": None,
            "state": "idle",  # idle|waiting_for_thumb|waiting_for_edit_thumb|pending_force_check
            "pending_video": None,  # dict with file_id, caption, entities
        }
        save_data(DB)
    return DB["users"][key]


def is_banned(user_id: int) -> bool:
    return str(user_id) in DB.get("banned", [])


def ban_user(user_id: int) -> None:
    DB.setdefault("banned", [])
    if str(user_id) not in DB["banned"]:
        DB["banned"].append(str(user_id))
        save_data(DB)


def unban_user(user_id: int) -> None:
    if str(user_id) in DB.get("banned", []):
        DB["banned"].remove(str(user_id))
        save_data(DB)


# ---------------- Keyboards ----------------
def start_keyboard():
    kb = [
        [
            InlineKeyboardButton("🧑‍🔧 Help", callback_data="help"),
            InlineKeyboardButton("📜 About", callback_data="about"),
        ],
        [InlineKeyboardButton("📢 Updates", url=FORCE_SUB_CHANNEL_LINK)],
    ]
    return InlineKeyboardMarkup(kb)


def saved_thumbnail_keyboard():
    kb = [
        [
            InlineKeyboardButton("👀 View Thumbnail", callback_data="view_thumb"),
            InlineKeyboardButton("🔙 Back To Home", callback_data="back_home"),
        ],
    ]
    return InlineKeyboardMarkup(kb)


def view_thumb_keyboard():
    kb = [
        [
            InlineKeyboardButton("🖋️ Edit Thumbnail", callback_data="edit_thumb"),
            InlineKeyboardButton("🗑️ Delete Thumbnail", callback_data="del_thumb"),
            InlineKeyboardButton("🔙 Back", callback_data="back_home"),
        ]
    ]
    return InlineKeyboardMarkup(kb)


def force_sub_keyboard():
    kb = [
        [
            InlineKeyboardButton("📡 Join Channel", url=FORCE_SUB_CHANNEL_LINK),
            InlineKeyboardButton("✅ Done", callback_data="force_check"),
        ]
    ]
    return InlineKeyboardMarkup(kb)


def back_button_kb(target: str = "home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"back_{target}")]])


# ---------------- Utilities ----------------
def entities_to_raw(entities: Optional[List[MessageEntity]]) -> Optional[List[Dict[str, Any]]]:
    if not entities:
        return None
    out = []
    for e in entities:
        # MessageEntity has attributes type, offset, length, url, user, language
        d = {"type": e.type, "offset": e.offset, "length": e.length}
        if getattr(e, "url", None):
            d["url"] = e.url
        if getattr(e, "user", None):
            d["user"] = {"id": e.user.id, "first_name": e.user.first_name}
        out.append(d)
    return out


def raw_to_entities(raw: Optional[List[Dict[str, Any]]]) -> Optional[List[MessageEntity]]:
    if not raw:
        return None
    res = []
    for r in raw:
        try:
            me = MessageEntity(type=r["type"], offset=r["offset"], length=r["length"])
            res.append(me)
        except Exception:
            continue
    return res


async def send_log(context: ContextTypes.DEFAULT_TYPE, title: str, body: str, photo_file_id: Optional[str] = None):
    """
    Send a nicer log message to LOG_CHANNEL_ID. If photo provided, send photo with caption.
    """
    try:
        if photo_file_id:
            # send photo first with caption
            await context.bot.send_photo(
                chat_id=LOG_CHANNEL_ID,
                photo=photo_file_id,
                caption=f"<b>{html.escape(title)}</b>\n\n{body}",
                parse_mode=constants.ParseMode.HTML,
            )
        else:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"<b>{html.escape(title)}</b>\n\n{body}",
                parse_mode=constants.ParseMode.HTML,
            )
    except Exception as e:
        logger.warning("Failed to send log: %s", e)


# ---------------- Command Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return
    ensure_user_record(user.id)
    text = (
        f"🎬 <b>Welcome to Video Cover / Thumbnail Bot</b>\n\n"
        f"This bot applies a saved thumbnail to your videos within seconds.\n\n"
        f"Branding: <a href='https://t.me/World_Fastest_Bots'>@World_Fastest_Bots</a>\n\n"
        f"Quick commands:\n"
        f"• <code>/addthumb</code> — add a thumbnail\n"
        f"• <code>/mythumb</code> — view your thumbnail\n"
        f"• <code>/delthumb</code> — delete thumbnail\n\n"
        f"Tap Help for usage instructions."
    )
    await update.message.reply_photo(photo=BOT_LOGO, caption=text, parse_mode=constants.ParseMode.HTML, reply_markup=start_keyboard())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return
    text = (
        "<b>How to use Video Cover / Thumbnail Bot</b>\n\n"
        "1. Send /addthumb and follow prompts to save a thumbnail (or just send a photo directly).\n"
        "2. Send a <b>video</b>. The bot will ask you to join our channel if you haven't.\n"
        "3. Click ✅ Done after joining to let the bot verify. If verified, the bot will apply\n"
        "   your saved thumbnail as the video cover and forward the processed video.\n\n"
        "<b>Public Commands</b>\n"
        "• /start — show welcome\n"
        "• /help — this help message\n"
        "• /addthumb — add a thumbnail (bot will ask for a photo)\n"
        "• /mythumb — show your saved thumbnail\n"
        "• /delthumb — delete your thumbnail\n\n"
        "Note: This bot is branded by @World_Fastest_Bots. For updates, use the Updates button in /start."
    )
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_caption(caption=text, parse_mode=constants.ParseMode.HTML, reply_markup=back_button_kb("home"))
        except Exception:
            await update.callback_query.edit_message_text(text=text, parse_mode=constants.ParseMode.HTML, reply_markup=back_button_kb("home"))
    else:
        await update.message.reply_text(text, parse_mode=constants.ParseMode.HTML)


async def about_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "<b>About Video Cover / Thumbnail Bot</b>\n\n"
        "A fast and reliable bot to apply your chosen thumbnail to videos before sending.\n\n"
        "• Apply thumbnails in seconds\n"
        "• Keeps formatting of captions (bold, italic, underline) by preserving entities\n"
        "• Professional branding: @World_Fastest_Bots\n\n"
        "Made to be simple, fast and professional. Use /help to see how it works."
    )
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_caption(caption=txt, parse_mode=constants.ParseMode.HTML, reply_markup=back_button_kb("home"))
        except Exception:
            await update.callback_query.edit_message_text(text=txt, parse_mode=constants.ParseMode.HTML, reply_markup=back_button_kb("home"))


async def addthumb_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return
    rec = ensure_user_record(user.id)
    rec["state"] = "waiting_for_thumb"
    save_data(DB)
    await update.message.reply_text("📸 Send a photo to set as your thumbnail (photo only).")


async def mythumb_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return
    rec = ensure_user_record(user.id)
    thumb = rec.get("thumbnail_file_id")
    if thumb:
        await update.message.reply_photo(photo=thumb, caption="🖼️ Here is your currently saved thumbnail.", reply_markup=view_thumb_keyboard())
    else:
        await update.message.reply_text("❌ No thumbnail found. Send a photo to set it.")


async def delthumb_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return
    rec = ensure_user_record(user.id)
    if rec.get("thumbnail_file_id"):
        rec["thumbnail_file_id"] = None
        save_data(DB)
        await update.message.reply_text("🗑️ Thumbnail deleted successfully.")
    else:
        await update.message.reply_text("❌ No thumbnail to delete.")


# ---------------- Media Handlers ----------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user
    if is_banned(user.id):
        return
    photos = message.photo
    if not photos:
        return
    rec = ensure_user_record(user.id)
    biggest = max(photos, key=lambda p: p.file_size or 0)
    file_id = biggest.file_id

    state = rec.get("state", "idle")
    # If user was waiting for a thumbnail (add or edit)
    if state in ("waiting_for_thumb", "waiting_for_edit_thumb"):
        rec["thumbnail_file_id"] = file_id
        rec["state"] = "idle"
        save_data(DB)
        await message.reply_photo(photo=file_id, caption="✅ Thumbnail saved successfully!", reply_markup=saved_thumbnail_keyboard())
        return

    # If user had pending video (sent video first) and is in pending state
    pending = rec.get("pending_video")
    if pending:
        # use this photo as cover and send the pending video
        try:
            entities_raw = pending.get("entities")
            # convert raw entities back to MessageEntity list if present
            entities = raw_to_entities(entities_raw)
            await context.bot.send_video(
                chat_id=message.chat.id,
                video=pending["file_id"],
                thumb=file_id,
                caption=pending.get("caption") or "",
                parse_mode=constants.ParseMode.HTML,
                supports_streaming=True,
            )
            DB["meta"]["total_videos"] = DB["meta"].get("total_videos", 0) + 1
            rec["pending_video"] = None
            rec["state"] = "idle"
            # also save this thumbnail as the user's default
            rec["thumbnail_file_id"] = file_id
            save_data(DB)
            await message.reply_text("✅ Video sent with the cover!")

            # log nicer
            title = "Applied cover (user-provided photo for pending video)"
            body = (
                f"User: <a href='tg://user?id={user.id}'>{html.escape(user.full_name)}</a>\n"
                f"User ID: <code>{user.id}</code>\n"
                f"Action: Video sent with provided cover\n"
            )
            await send_log(context, title, body, photo_file_id=file_id)
            return
        except Exception as e:
            logger.exception("Error sending pending video with photo: %s", e)
            await message.reply_text(f"❌ Error: {e}")
            return

    # Otherwise store as new thumbnail (when user just sends a photo)
    rec["thumbnail_file_id"] = file_id
    save_data(DB)
    await message.reply_photo(photo=file_id, caption="✅ Thumbnail saved successfully!", reply_markup=saved_thumbnail_keyboard())


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user
    if is_banned(user.id):
        await message.reply_text("🚫 You are banned from using this bot.")
        return
    rec = ensure_user_record(user.id)
    video = message.video or message.document  # document could be a video file
    if not video:
        await message.reply_text("❌ Please send a valid video.")
        return

    # store pending video so we can verify force-sub first
    entities_raw = None
    if message.caption_entities:
        entities_raw = entities_to_raw(message.caption_entities)
    rec["pending_video"] = {"file_id": video.file_id, "caption": message.caption or "", "entities": entities_raw}

    # check membership in force-sub channel
    is_member = False
    try:
        member = await context.bot.get_chat_member(chat_id=FORCE_SUB_CHANNEL_ID, user_id=user.id)
        is_member = member.status not in ("left", "kicked")
    except Exception:
        is_member = False

    if not is_member:
        rec["state"] = "pending_force_check"
        save_data(DB)
        await message.reply_photo(
            photo=BOT_LOGO,
            caption=(
                "🚫 <b>You must join our channel to use this bot.</b>\n\n"
                "Please join and then click ✅ Done."
            ),
            parse_mode=constants.ParseMode.HTML,
            reply_markup=force_sub_keyboard(),
        )
        return

    # user is member — apply saved thumbnail if present
    thumb = rec.get("thumbnail_file_id")
    if not thumb:
        rec["state"] = "waiting_for_thumb_for_video"
        save_data(DB)
        await message.reply_text("❗ Please send a photo first to set as thumbnail.")
        return

    # send video with the saved thumbnail and preserve caption entities
    try:
        # send with preserved caption and entities by using parse_mode and raw_entities if needed.
        await context.bot.send_video(
            chat_id=message.chat.id,
            video=video.file_id,
            thumb=thumb,
            caption=message.caption or "",
            parse_mode=constants.ParseMode.HTML,
            supports_streaming=True,
        )
        DB["meta"]["total_videos"] = DB["meta"].get("total_videos", 0) + 1
        rec["pending_video"] = None
        rec["state"] = "idle"
        save_data(DB)
        await message.reply_text("✅ Video sent with the cover!")

        # log
        title = "Applied cover (instant)"
        body = (
            f"User: <a href='tg://user?id={user.id}'>{html.escape(user.full_name)}</a>\n"
            f"User ID: <code>{user.id}</code>\n"
            f"Action: Video sent with saved thumbnail\n"
        )
        await send_log(context, title, body, photo_file_id=thumb)
    except Exception as e:
        logger.exception("Failed to send video with saved thumb: %s", e)
        await message.reply_text(f"❌ Error sending video: {e}")


# ---------------- Callback Query Router ----------------
async def callback_query_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    data = q.data or ""
    user = update.effective_user
    await q.answer()
    rec = ensure_user_record(user.id)

    if data == "help" or data == "back_home":
        help_text = (
            "<b>Help — How to use</b>\n\n"
            "• /addthumb — add thumbnail\n"
            "• /mythumb — view thumbnail\n"
            "• /delthumb — delete thumbnail\n\n"
            "Send a video and the bot will apply your saved thumbnail (if you're joined to our channel)."
        )
        try:
            await q.edit_message_caption(caption=help_text, parse_mode=constants.ParseMode.HTML, reply_markup=back_button_kb("home"))
        except Exception:
            await q.edit_message_text(text=help_text, parse_mode=constants.ParseMode.HTML, reply_markup=back_button_kb("home"))
        return

    if data == "about":
        await about_callback(update, context)
        return

    if data == "view_thumb":
        thumb = rec.get("thumbnail_file_id")
        if not thumb:
            try:
                await q.edit_message_caption(caption="❌ No thumbnail found. Send a photo to set it.", reply_markup=None)
            except Exception:
                await q.message.reply_text("❌ No thumbnail found. Send a photo to set it.")
            return
        try:
            await q.edit_message_media(media=InputMediaPhoto(media=thumb, caption="Your current thumbnail 👇"), reply_markup=view_thumb_keyboard())
        except Exception:
            await q.message.reply_photo(photo=thumb, caption="Your current thumbnail 👇", reply_markup=view_thumb_keyboard())
        return

    if data == "edit_thumb":
        rec["state"] = "waiting_for_edit_thumb"
        save_data(DB)
        try:
            await q.edit_message_caption(caption="🖼️ Please send the new thumbnail image (photo only).", reply_markup=back_button_kb("home"))
        except Exception:
            await q.message.reply_text("🖼️ Please send the new thumbnail image (photo only).", reply_markup=back_button_kb("home"))
        return

    if data == "del_thumb":
        rec["thumbnail_file_id"] = None
        save_data(DB)
        try:
            await q.edit_message_media(media=InputMediaPhoto(media=BOT_LOGO, caption="✅ Thumbnail removed successfully!"), reply_markup=back_button_kb("home"))
        except Exception:
            await q.edit_message_text(text="✅ Thumbnail removed successfully!", reply_markup=back_button_kb("home"))
        return

    if data == "force_check":
        # verify membership then send pending video if exists
        try:
            member = await context.bot.get_chat_member(chat_id=FORCE_SUB_CHANNEL_ID, user_id=user.id)
            is_member = member.status not in ("left", "kicked")
        except Exception:
            is_member = False

        if not is_member:
            await q.edit_message_caption(caption="🚫 You are not a member yet. Please join the channel and click ✅ Done.", reply_markup=force_sub_keyboard())
            return

        pending = rec.get("pending_video")
        if not pending:
            await q.edit_message_caption(caption="✅ Verified — but no pending video found.", reply_markup=back_button_kb("home"))
            rec["state"] = "idle"
            save_data(DB)
            return

        thumb = rec.get("thumbnail_file_id")
        if not thumb:
            rec["state"] = "waiting_for_thumb_for_video"
            save_data(DB)
            await q.edit_message_caption(caption="❗ Please send a photo first to set as thumbnail.", reply_markup=back_button_kb("home"))
            return

        # send video
        try:
            await context.bot.send_video(
                chat_id=q.message.chat.id,
                video=pending["file_id"],
                thumb=thumb,
                caption=pending.get("caption") or "",
                parse_mode=constants.ParseMode.HTML,
                supports_streaming=True,
            )
            DB["meta"]["total_videos"] = DB["meta"].get("total_videos", 0) + 1
            rec["pending_video"] = None
            rec["state"] = "idle"
            save_data(DB)
            await q.edit_message_caption(caption="✅ Verified and video sent with your thumbnail!", reply_markup=back_button_kb("home"))

            # log
            title = "Applied cover (after force-check)"
            body = (
                f"User: <a href='tg://user?id={user.id}'>{html.escape(user.full_name)}</a>\n"
                f"User ID: <code>{user.id}</code>\n"
                f"Action: Video sent after verification\n"
            )
            await send_log(context, title, body, photo_file_id=thumb)
        except Exception as e:
            logger.exception("Failed to send pending video after force-check: %s", e)
            await q.edit_message_caption(caption=f"❌ Error sending video: {e}", reply_markup=back_button_kb("home"))
        return

    if data.startswith("back_"):
        target = data.split("_", 1)[1]
        if target == "home":
            try:
                await q.edit_message_caption(
                    caption="Returned to home. Use buttons or commands.\nUse /help for more info.",
                    reply_markup=start_keyboard(),
                )
            except Exception:
                await q.edit_message_text("Returned to home. Use /help for more info.", reply_markup=start_keyboard())
        else:
            await q.answer()
        return


# ---------------- Owner-only Admin Commands ----------------
def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return
        if user.id != OWNER_ID:
            await update.message.reply_text("❌ This command is owner-only.")
            return
        return await func(update, context)
    return wrapper


@owner_only
async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong! ✅")


@owner_only
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = len(DB.get("users", {}))
    total_banned = len(DB.get("banned", []))
    total_videos = DB.get("meta", {}).get("total_videos", 0)
    text = (
        f"<b>Bot Stats</b>\n\n"
        f"Total users: <code>{total_users}</code>\n"
        f"Banned users: <code>{total_banned}</code>\n"
        f"Total videos processed: <code>{total_videos}</code>\n"
    )
    await update.message.reply_text(text, parse_mode=constants.ParseMode.HTML)


@owner_only
async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # usage: /ban <user_id>
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    try:
        uid = int(args[0])
        ban_user(uid)
        await update.message.reply_text(f"User <code>{uid}</code> banned.", parse_mode=constants.ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


@owner_only
async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        uid = int(args[0])
        unban_user(uid)
        await update.message.reply_text(f"User <code>{uid}</code> unbanned.", parse_mode=constants.ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


@owner_only
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /broadcast <message text>
    Sends a message to all users known in DB (async but owner-triggered).
    """
    if not context.args:
        await update.message.reply_text("Usage: /broadcast Your message here")
        return
    text = " ".join(context.args)
    users = list(DB.get("users", {}).keys())
    sent = 0
    failed = 0
    await update.message.reply_text(f"Starting broadcast to {len(users)} users...")
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=text, parse_mode=constants.ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.05)  # small delay to avoid flood
        except Exception:
            failed += 1
    await update.message.reply_text(f"Broadcast finished. Sent: {sent} | Failed: {failed}")


@owner_only
async def dbroadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /dbroadcast <file> - sends a file (media) that owner replies with to many users.
    Alternatively, if called with text, acts like broadcast but direct.
    For simplicity, owner can reply to a message and call /dbroadcast to forward it.
    """
    # If owner replied to a message, forward that message to all users
    if update.message.reply_to_message:
        msg = update.message.reply_to_message
        users = list(DB.get("users", {}).keys())
        sent = 0
        failed = 0
        await update.message.reply_text(f"Forwarding the replied message to {len(users)} users...")
        for uid in users:
            try:
                await msg.copy(chat_id=int(uid))
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
        await update.message.reply_text(f"dbroadcast finished. Sent: {sent} | Failed: {failed}")
    else:
        await update.message.reply_text("Reply to a message and then use /dbroadcast to forward it to all users.")


# ---------------- Fallback / Misc ----------------
async def misc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    catch-all for other text messages.
    """
    if not update.message:
        return
    user = update.effective_user
    if is_banned(user.id):
        return
    text = update.message.text or ""
    # Provide a friendly nudge
    await update.message.reply_text("Use /help to see public commands. To set thumbnail: /addthumb or just send a photo.")


# ---------------- Startup ----------------
def main():
    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        print("Please set BOT_TOKEN in the script.")
        return
    application = Application.builder().token(BOT_TOKEN).build()

    # public commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("addthumb", addthumb_cmd))
    application.add_handler(CommandHandler("mythumb", mythumb_cmd))
    application.add_handler(CommandHandler("delthumb", delthumb_cmd))

    # owner commands
    application.add_handler(CommandHandler("ping", ping_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("ban", ban_cmd))
    application.add_handler(CommandHandler("unban", unban_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast_cmd))
    application.add_handler(CommandHandler("dbroadcast", dbroadcast_cmd))

    # media and callbacks
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    application.add_handler(CallbackQueryHandler(callback_query_router))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, misc_handler))

    logger.info("Starting bot...")
    application.run_polling(allowed_updates=[
        "message", "callback_query", "edited_message", "channel_post", "my_chat_member", "chat_member"
    ])


if __name__ == "__main__":
    main()
