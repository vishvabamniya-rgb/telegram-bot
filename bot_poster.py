from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

# ============ CONFIG ============

api_id = 31380839
api_hash = "d27a8c4fdfd3968c8e2e143450581c09"
bot_token = "8201833646:AAGOnTm2ARso6WYFvQXGRRd5uG4YNfxONYc"

DELIVERY_BOT_USERNAME = "Rezei_bot"  # without @

STORAGE_CHANNEL = -1003884933686

PROMO_CHANNELS = {
    "channel1": -1003626369643,
    "channel2": -1003772304035,
    "channel3": -1003858044467
}

# =================================

bot = Client("poster_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

conn = sqlite3.connect("files.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS files (
    file_id TEXT,
    group_name TEXT
)
""")
conn.commit()

current_group = None
waiting_for_post = {}

# ========= SAVE MEDIA =========

@bot.on_message(filters.chat(STORAGE_CHANNEL))
async def save_media(client, message):
    global current_group

    if not current_group:
        return

    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        return

    cursor.execute("INSERT INTO files VALUES (?, ?)", (file_id, current_group))
    conn.commit()

# ========= SET GROUP =========

@bot.on_message(filters.command("setgroup"))
async def set_group(client, message):
    global current_group

    if len(message.command) < 2:
        await message.reply("Usage: /setgroup groupname")
        return

    current_group = message.command[1]
    await message.reply(f"✅ Group set to: {current_group}")

# ========= CREATE POST =========

@bot.on_message(filters.command("post"))
async def start_post(client, message):

    if len(message.command) < 3:
        await message.reply("Usage:\n/post groupname category")
        return

    group = message.command[1]
    category = message.command[2].lower()

    if category not in PROMO_CHANNELS:
        await message.reply("❌ Invalid category.")
        return

    waiting_for_post[message.chat.id] = (group, category)

    await message.reply("📸 Send poster image with caption.")

@bot.on_message(filters.photo)
async def create_post(client, message):

    if message.chat.id not in waiting_for_post:
        return

    group, category = waiting_for_post.pop(message.chat.id)
    channel_id = PROMO_CHANNELS[category]

    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "⬇ Download",
                url=f"https://t.me/{DELIVERY_BOT_USERNAME}?start={group}"
            )
        ]]
    )

    await bot.send_photo(
        chat_id=channel_id,
        photo=message.photo.file_id,
        caption=message.caption if message.caption else "",
        reply_markup=keyboard
    )

    await message.reply("✅ Posted successfully.")

# =================================

bot.run()
