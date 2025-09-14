from pyrogram import Client, filters

API_ID = 
API_HASH = ""
BOT_TOKEN = ""

app = Client("cover-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
covers = {}

@app.on_message(filters.photo)
async def save_cover(c, m):
    covers[m.from_user.id] = m.photo.file_id
    await m.reply("✅ Cover saved!")

@app.on_message(filters.video)
async def apply_cover(c, m):
    cover = covers.get(m.from_user.id)
    await c.send_video(m.chat.id, m.video.file_id, caption="**Video with cover**", cover=cover)

app.run()
