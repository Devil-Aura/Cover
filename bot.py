import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# ========================
# CONFIG
# ========================
API_ID =       # apna api_id dalo
API_HASH = ""
BOT_TOKEN = ""

app = Client("cover-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# In-memory storage (restart hone par reset hoga)
user_covers = {}


# ========================
# COMMANDS
# ========================
@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply("👋 Send me a photo to set as your cover, then send a video!")

@app.on_message(filters.command("show_cover"))
async def show_cover(_, message: Message):
    cover = user_covers.get(message.from_user.id)
    if cover:
        await message.reply_photo(cover, caption="📸 Your Current Cover")
    else:
        await message.reply("❌ You don't have any cover set.")

@app.on_message(filters.command("del_cover"))
async def del_cover(_, message: Message):
    if message.from_user.id in user_covers:
        del user_covers[message.from_user.id]
        await message.reply("🗑️ Your cover deleted.")
    else:
        await message.reply("❌ You don't have any cover to delete.")


# ========================
# MEDIA HANDLERS
# ========================
@app.on_message(filters.photo)
async def save_cover(_, message: Message):
    file_id = message.photo.file_id
    user_covers[message.from_user.id] = file_id
    await message.reply("✅ Your new cover saved!")


@app.on_message(filters.video)
async def apply_cover(_, message: Message):
    cover = user_covers.get(message.from_user.id)
    if not cover:
        return await message.reply("❌ No cover set. Send an image first!")

    video = message.video
    caption = message.caption or ""

    try:
        await app.send_video(
            chat_id=message.chat.id,
            video=video.file_id,
            caption=caption,
            thumb=cover  # 👈 thumbnail apply here
        )
    except Exception as e:
        print(e)
        await message.reply("⚠️ Failed to apply cover.")


# ========================
# START BOT
# ========================
app.run()
