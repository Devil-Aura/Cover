import asyncio
from pyrogram import Client, filters

API_ID =    # apna API ID
API_HASH = ""
BOT_TOKEN = ""

app = Client("cover-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# memory me per-user thumbnail
user_thumbs = {}


# ========================
# COMMANDS
# ========================
@app.on_message(filters.command("start"))
async def start(_, m):
    await m.reply("👋 Reply any photo with /set_thumb to save thumbnail!")


@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m):
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("⚠️ Reply to a photo with /set_thumb")

    file_id = m.reply_to_message.photo.file_id
    user_thumbs[m.from_user.id] = file_id
    await m.reply("✅ Thumbnail saved successfully!")


@app.on_message(filters.command("show_thumb"))
async def show_thumb(_, m):
    thumb = user_thumbs.get(m.from_user.id)
    if thumb:
        await m.reply_photo(thumb, caption="📸 Your current thumbnail")
    else:
        await m.reply("❌ No thumbnail set.")


@app.on_message(filters.command("del_thumb"))
async def del_thumb(_, m):
    if m.from_user.id in user_thumbs:
        del user_thumbs[m.from_user.id]
        await m.reply("🗑️ Thumbnail deleted.")
    else:
        await m.reply("❌ No thumbnail to delete.")


# ========================
# VIDEO HANDLER
# ========================
@app.on_message(filters.video)
async def handle_video(_, m):
    thumb = user_thumbs.get(m.from_user.id)

    try:
        await app.send_video(
            chat_id=m.chat.id,
            video=m.video.file_id,
            caption=m.caption or "",
            cover=thumb  # 👈 PyroFork supports this
        )
    except Exception as e:
        await m.reply(f"⚠️ Failed to apply thumbnail.\n`{e}`")


# ========================
# START
# ========================
print("✅ Bot running...")
app.run()
