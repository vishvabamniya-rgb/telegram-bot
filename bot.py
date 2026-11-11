from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import random
import string
import requests
import asyncio
import time

def generate_token(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# ================= CONFIG =================

api_id = 31380839
api_hash = "d27a8c4fdfd3968c8e2e143450581c09"
bot_token = "8689296852:AAH-5rx-TvJ5nse2Q1C0fgfqrGhM-def6vI"

BOT_USERNAME = "Rezei_bot"  # without @

AROLINKS_API = "1cb0154fba7416bc8dfbce81779f6184b097386f"

def shorten_link(long_url):
    api_url = f"https://arolinks.com/api?api={AROLINKS_API}&url={long_url}"

    response = requests.get(api_url)
    data = response.json()

    if data["status"] == "success":
        return data["shortenedUrl"]
    else:
        return long_url

STORAGE_CHANNEL = -1003884933686  # your storage channel id

PROMO_CHANNELS = {
    "western": -1003626369643,
    "jav": -1003772304035,
    "comatozze": -1003858044467,
    "sunny": -1003808345264,
    "indian": -1003743737098
}

# ==========================================

bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

conn = sqlite3.connect("files.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS files (
    file_id TEXT,
    group_name TEXT,
    caption TEXT,
    reply_text TEXT
)
""")
conn.commit()

# 🔐 TOKENS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS tokens (
    user_id INTEGER,
    group_name TEXT,
    token TEXT,
    used INTEGER DEFAULT 0
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS expiry (
    chat_id INTEGER,
    message_id INTEGER,
    expire_at INTEGER,
    is_warning INTEGER DEFAULT 0
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS post_clicks (
    post_id TEXT PRIMARY KEY,
    clicks INTEGER DEFAULT 0
)
""")
conn.commit()

current_group = None
waiting_for_post = {}

# ================= SAVE MEDIA =================

@bot.on_message(filters.chat(STORAGE_CHANNEL) & filters.media)
async def save_media(client, message):
    global current_group

    if not current_group:
        return

    file_id = None

    if message.video:
        file_id = message.video.file_id
    elif message.photo:
        file_id = message.photo.file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.animation:
        file_id = message.animation.file_id
    elif message.voice:
        file_id = message.voice.file_id

    if not file_id:
        return

    caption = message.caption if message.caption else None

    # Detect reply text
    reply_text = None
    if message.reply_to_message and message.reply_to_message.text:
        reply_text = message.reply_to_message.text

    cursor.execute(
        "INSERT INTO files VALUES (?, ?, ?, ?)",
        (file_id, current_group, caption, reply_text)
    )
    conn.commit()

    print("Saved:", file_id)

@bot.on_message(filters.chat(STORAGE_CHANNEL) & filters.text)
async def save_reply_text(client, message):

    if not message.reply_to_message:
        return

    replied = message.reply_to_message
    file_id = None

    if replied.video:
        file_id = replied.video.file_id
    elif replied.photo:
        file_id = replied.photo.file_id
    elif replied.document:
        file_id = replied.document.file_id
    elif replied.audio:
        file_id = replied.audio.file_id
    elif replied.animation:
        file_id = replied.animation.file_id
    elif replied.voice:
        file_id = replied.voice.file_id

    if not file_id:
        return

    reply_text = message.text

    cursor.execute(
        "UPDATE files SET reply_text=? WHERE file_id=?",
        (reply_text, file_id)
    )
    conn.commit()

    print("Reply updated for:", file_id)

# ================= SET GROUP =================

@bot.on_message(filters.command("setgroup"))
async def set_group(client, message):
    global current_group

    if len(message.command) < 2:
        await message.reply("Usage: /setgroup groupname")
        return

    current_group = message.command[1]
    await message.reply(f"✅ Group set to: {current_group}")

# ================= CREATE POST =================

@bot.on_message(filters.command("post"))
async def start_post(client, message):

    print("START TRIGGERED")
    print(message.text)

    if len(message.command) < 3:
        await message.reply("Usage:\n/post groupname channelkey")
        return

    group = message.command[1]
    category = message.command[2].lower()

    if category not in PROMO_CHANNELS:
        await message.reply("❌ Invalid channel key.")
        return

    waiting_for_post[message.chat.id] = (group, category)
    await message.reply("📸 Send poster image with caption now.")

@bot.on_message(filters.photo | filters.video)
async def create_post(client, message):

    if message.chat.id not in waiting_for_post:
        return

    group, category = waiting_for_post.pop(message.chat.id)
    channel_id = PROMO_CHANNELS[category]

    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "Download",
                url=f"https://t.me/{BOT_USERNAME}?start={group}"
            )
        ]]
    )

    try:
        if message.photo:
            await bot.send_photo(
                chat_id=channel_id,
                photo=message.photo.file_id,
                caption=message.caption if message.caption else "",

            caption_entities=message.caption_entities if message.caption else None,
                reply_markup=keyboard
            )

        elif message.video:
            await bot.send_video(
                chat_id=channel_id,
                video=message.video.file_id,
                caption=message.caption if message.caption else "",

            caption_entities=message.caption_entities if message.caption else None,
                reply_markup=keyboard
            )

        await message.reply(f"✅ Posted in {category}")

    except Exception as e:
        print("POST ERROR:", e)
        await message.reply(f"❌ Error posting: {e}")

# ================= START HANDLER =================

@bot.on_message(filters.private & filters.command(["start"]))
async def start_handler(client, message):

    click_count = 0

    if message.command[0] != "start":
        return

    if len(message.command) > 1:
        param = message.command[1]

        # 🔓 UNLOCK FLOW
        if param.startswith("unlock_"):

            token = param.replace("unlock_", "")

            cursor.execute(
                "SELECT user_id, group_name, used FROM tokens WHERE token=?",
                (token,)
            )
            data = cursor.fetchone()

            if not data:
                await message.reply("❌ Invalid link.")
                return

            token_user_id, group, used = data

            if used == 1:
                await message.reply("⛔ This link was already used.")
                return

            if message.from_user.id != token_user_id:
                await message.reply("⛔ This link does not belong to you.")
                return

            post_id = group

            # Insert if not exists
            cursor.execute(
                "INSERT OR IGNORE INTO post_clicks (post_id, clicks) VALUES (?, 0)",
                (post_id,)
            )

            # Increase click count
            cursor.execute(
                "UPDATE post_clicks SET clicks = clicks + 1 WHERE post_id = ?",
                (post_id,)
            )

            conn.commit()

            # Fetch updated count
            cursor.execute(
                "SELECT clicks FROM post_clicks WHERE post_id = ?",
                (post_id,)
            )

            result = cursor.fetchone()
            click_count = result[0] if result else 0

            # Send files
            cursor.execute(
                "SELECT file_id, caption, reply_text FROM files WHERE group_name=?",
                (group,)
            )
            files = cursor.fetchall()
            print("Files fetched:", files)

            if not files:
                await message.reply("❌ No files found.")
                return

            sent_messages = []

            for file in files:
                file_id = file[0]
                caption = file[1]
                reply_text = file[2]

                try:
                    sent = await client.send_cached_media(
                        chat_id=message.chat.id,
                        file_id=file_id,
                        caption=caption
                    )
                    sent_messages.append(sent)

                    expire_at = int(time.time()) + 900  # 15 minutes

                    cursor.execute(
                        "INSERT INTO expiry VALUES (?, ?, ?, 0)",
                        (sent.chat.id, sent.id, expire_at)
                    )
                    conn.commit()

                    if reply_text:
                        reply_msg = await client.send_message(
                            chat_id=message.chat.id,
                            text=reply_text
                        )
                        sent_messages.append(reply_msg)

                        expire_at = int(time.time()) + 900

                        cursor.execute(
                            "INSERT INTO expiry VALUES (?, ?, ?, 0)",
                            (reply_msg.chat.id, reply_msg.id, expire_at)
                        )
                        conn.commit()

                except Exception as e:
                    print("Error sending:", e)
                    continue

            warning = await message.reply_text(
                "⚠️ These files will auto delete in 15 minutes.\n"
                "Please download or save them now!"
            )

            expire_at = int(time.time()) + 900

            cursor.execute(
                "INSERT INTO expiry VALUES (?, ?, ?, 1)",
                (warning.chat.id, warning.id, expire_at)
            )
            conn.commit()

            cursor.execute(
                "UPDATE tokens SET used=1 WHERE token=?",
                (token,)
            )
            conn.commit()

            return

        # 🔐 GENERATE TOKEN FLOW
        else:

            group = param

            post_id = group
            cursor.execute(
                "SELECT clicks FROM post_clicks WHERE post_id = ?",
                (post_id,)
            )
            result = cursor.fetchone()
            click_count = result[0] if result else 0

            token = generate_token()

            cursor.execute(
                "INSERT INTO tokens (user_id, group_name, token, used) VALUES (?, ?, ?, ?)",
                (message.from_user.id, group, token, 0)
            )
            conn.commit()

            unlock_link = f"https://t.me/{BOT_USERNAME}?start=unlock_{token}"

            # Send loading message
            msg = await message.reply("⏳ Generating your secure link...")

            # Replace with your Arolinks short link later
            short_link = shorten_link(unlock_link)

            # Delete loading message
            await msg.delete()

            keyboard = InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("Link", url=short_link),
                    InlineKeyboardButton("Tutorial", url="https://t.me/linktutorial101")
                ]]
            )

            await message.reply(
                f"📊 Total Clicks: {click_count}\n\n"
                "👇 Here's your link – Complete steps to unlock:",
                reply_markup=keyboard
            )
            return

    else:
        await message.reply("👋 Welcome!")

# ===== AUTO APPROVE JOIN REQUEST =====
@bot.on_chat_join_request()
async def auto_approve(client, join_request):
    await client.approve_chat_join_request(
        chat_id=join_request.chat.id,
        user_id=join_request.from_user.id
    )

    try:
        await client.send_message(
            join_request.from_user.id,
            "✅ Your join request has been approved!"
        )
    except:
        pass

# ================= EXPIRY CHECKER =================

async def expiry_checker():
    while True:
        print("Checker active")

        now = int(time.time())

        cursor.execute(
            "SELECT chat_id, message_id, is_warning FROM expiry WHERE expire_at <= ?",
            (now,)
        )
        rows = cursor.fetchall()

        for chat_id, message_id, is_warning in rows:
            try:
                if is_warning == 1:
                    await bot.edit_message_text(
                        chat_id,
                        message_id,
                        "❌ Files expired."
                    )
                else:
                    await bot.delete_messages(chat_id, message_id)

                cursor.execute(
                    "DELETE FROM expiry WHERE chat_id=? AND message_id=?",
                    (chat_id, message_id)
                )
                conn.commit()

            except Exception as e:
                print("Delete error:", e)

        await asyncio.sleep(30)

# Start expiry checker once
bot.loop.create_task(expiry_checker())

# ================= RUN =================

bot.run()
