from pyrogram import Client, filters
import sqlite3

# ============ CONFIG ============

api_id = 31380839
api_hash = "d27a8c4fdfd3968c8e2e143450581c09"
bot_token = "8485426843:AAGdXJRcKCb7ZoI-YUBl32RgP_xmP10Ujdc"

# =================================

bot = Client("delivery_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

conn = sqlite3.connect("files.db", check_same_thread=False)
cursor = conn.cursor()

# ========= START HANDLER =========

@bot.on_message(filters.command("start"))
async def start_handler(client, message):

    if len(message.command) > 1:
        group = message.command[1]

        cursor.execute("SELECT file_id FROM files WHERE group_name=?", (group,))
        files = cursor.fetchall()

        if not files:
            await message.reply("❌ No files found.")
            return

        for file in files:
            await message.reply_video(file[0])

        await message.reply("✅ All files sent successfully!")

    else:
        await message.reply("👋 Welcome!")

# =================================

bot.run()
