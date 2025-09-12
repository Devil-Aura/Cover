import logging
from aiogram import Bot, Dispatcher, executor, types

API_TOKEN = ""  # apna bot token yaha daalna

# Logging enable
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot & Dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# In-memory thumbnail storage (restart hone par reset)
user_thumbs = {}


# ========================
# COMMANDS
# ========================
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.reply("👋 Reply any photo with /set_thumb to save thumbnail!")


@dp.message_handler(commands=["set_thumb"])
async def cmd_set_thumb(message: types.Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply("⚠️ Reply to a photo with /set_thumb")

    file_id = message.reply_to_message.photo[-1].file_id
    user_thumbs[message.from_user.id] = file_id
    await message.reply("✅ Thumbnail saved successfully!")


@dp.message_handler(commands=["show_thumb"])
async def cmd_show_thumb(message: types.Message):
    thumb = user_thumbs.get(message.from_user.id)
    if thumb:
        await bot.send_photo(message.chat.id, thumb, caption="📸 Your current thumbnail")
    else:
        await message.reply("❌ No thumbnail set.")


@dp.message_handler(commands=["del_thumb"])
async def cmd_del_thumb(message: types.Message):
    if message.from_user.id in user_thumbs:
        del user_thumbs[message.from_user.id]
        await message.reply("🗑️ Thumbnail deleted.")
    else:
        await message.reply("❌ No thumbnail to delete.")


# ========================
# VIDEO HANDLER
# ========================
@dp.message_handler(content_types=["video"])
async def handle_video(message: types.Message):
    thumb = user_thumbs.get(message.from_user.id)

    try:
        await bot.send_video(
            chat_id=message.chat.id,
            video=message.video.file_id,
            caption=message.caption or "",
            thumb=thumb  # 👈 yaha thumbnail apply hoga
        )
    except Exception as e:
        logger.error(f"Video Thumbnail Error: {e}")
        await message.reply("⚠️ Failed to apply thumbnail.")


# ========================
# START BOT
# ========================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
