import os
import sys
import asyncio
import time
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message

# ========================
# CONFIG
# ========================
API_ID =       # your api_id
API_HASH = ""
BOT_TOKEN = ""
OWNER_ID =  # your telegram user id

app = Client("cover-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ========================
# DATABASE
# ========================
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
# Now per-user cover (instead of global)
cursor.execute("CREATE TABLE IF NOT EXISTS covers (user_id INTEGER PRIMARY KEY, file_id TEXT)")
conn.commit()

# ========================
# HELPERS
# ========================
def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    cursor.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def save_cover(user_id, file_id):
    cursor.execute("REPLACE INTO covers (user_id, file_id) VALUES (?, ?)", (user_id, file_id))
    conn.commit()

def get_cover(user_id):
    cursor.execute("SELECT file_id FROM covers WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None

def del_cover(user_id):
    cursor.execute("DELETE FROM covers WHERE user_id=?", (user_id,))
    conn.commit()

# ========================
# COMMANDS
# ========================
@app.on_message(filters.command("ping"))
async def ping(_, m: Message):
    start = time.time()
    reply = await m.reply("Pinging...")
    end = time.time()
    await reply.edit_text(f"🏓 Pong! `{round((end-start)*1000)} ms`")

@app.on_message(filters.command("restart") & filters.user(OWNER_ID))
async def restart(_, m: Message):
    await m.reply("♻️ Restarting...")
    os.execv(sys.executable, ['python'] + sys.argv)

@app.on_message(filters.command("show_cover"))
async def show_cover(_, m: Message):
    cover = get_cover(m.from_user.id)
    if cover:
        await m.reply_photo(cover, caption="📸 Your Current Cover")
    else:
        await m.reply("❌ You don't have any cover set.")

@app.on_message(filters.command("del_cover"))
async def delete_cover(_, m: Message):
    del_cover(m.from_user.id)
    await m.reply("🗑️ Your cover deleted.")

@app.on_message(filters.command("users"))
async def show_users(_, m: Message):
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    await m.reply(f"👥 Total users: `{count}`")

@app.on_message(filters.command("stats"))
async def stats(_, m: Message):
    cursor.execute("SELECT COUNT(*) FROM users")
    ucount = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM admins")
    acount = cursor.fetchone()[0]
    await m.reply(f"📊 Stats:\n👥 Users: `{ucount}`\n👮 Admins: `{acount}`")

@app.on_message(filters.command("addadmin") & filters.user(OWNER_ID))
async def add_admin(_, m: Message):
    if len(m.command) < 2:
        return await m.reply("Usage: /addadmin user_id")
    uid = int(m.command[1])
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (uid,))
    conn.commit()
    await m.reply(f"✅ User `{uid}` added as admin.")

@app.on_message(filters.command("removeadmin") & filters.user(OWNER_ID))
async def remove_admin(_, m: Message):
    if len(m.command) < 2:
        return await m.reply("Usage: /removeadmin user_id")
    uid = int(m.command[1])
    cursor.execute("DELETE FROM admins WHERE user_id=?", (uid,))
    conn.commit()
    await m.reply(f"🗑️ User `{uid}` removed from admins.")

@app.on_message(filters.command("showadmin"))
async def show_admins(_, m: Message):
    cursor.execute("SELECT user_id FROM admins")
    rows = cursor.fetchall()
    text = "👮 Admins:\n"
    text += "\n".join([f"- `{r[0]}`" for r in rows]) if rows else "No admins."
    await m.reply(text)

@app.on_message(filters.command("dbroadcast") & filters.user([OWNER_ID]))
async def dbroadcast(_, m: Message):
    if not m.reply_to_message:
        return await m.reply("Reply to a message with /dbroadcast <seconds>")
    try:
        seconds = int(m.command[1]) if len(m.command) > 1 else 0
    except:
        seconds = 0

    cursor.execute("SELECT user_id FROM users")
    users = [u[0] for u in cursor.fetchall()]
    sent = 0
    for uid in users:
        try:
            msg = await m.reply_to_message.copy(uid)  # copies with all formatting, buttons, media
            if seconds > 0:
                asyncio.create_task(delete_after(msg, seconds))
            sent += 1
        except Exception:
            pass
    await m.reply(f"📢 Broadcast sent to {sent} users.")

async def delete_after(msg: Message, seconds: int):
    await asyncio.sleep(seconds)
    try:
        await msg.delete()
    except:
        pass

# ========================
# MEDIA HANDLERS
# ========================
@app.on_message(filters.photo)
async def save_photo_cover(_, m: Message):
    add_user(m.from_user.id)
    save_cover(m.from_user.id, m.photo.file_id)
    await m.reply("✅ Your new cover saved!")

@app.on_message(filters.video)
async def video_handler(_, m: Message):
    add_user(m.from_user.id)
    cover = get_cover(m.from_user.id)
    caption = m.caption or ""
    if is_admin(m.from_user.id):
        caption = f"**{caption}**"
    if cover:
        try:
            await m.reply_video(
                video=m.video.file_id,
                caption=caption,
                thumb=cover
            )
        except Exception as e:
            await m.reply(f"⚠️ Failed to apply cover: {e}")
    else:
        await m.reply("❌ No cover set. Send an image first!")

# ========================
# START
# ========================
@app.on_message(filters.command("start"))
async def start(_, m: Message):
    add_user(m.from_user.id)
    await m.reply("👋 Welcome! Send me a photo to set your own cover, then send a video to apply it.")

print("✅ Bot running...")
app.run()
