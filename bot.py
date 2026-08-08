import re
import logging
import sqlite3
import base58
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
ADMIN_ID = 7857565977

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def init_db():
    conn = sqlite3.connect("verifications.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            post_link TEXT,
            sol_address TEXT,
            photo_file_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_submission(user_id: int, username: str, post_link: str, sol_address: str, photo_file_id: str = None):
    conn = sqlite3.connect("verifications.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO submissions (user_id, username, post_link, sol_address, photo_file_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, post_link, sol_address, photo_file_id)
        )
        entry_id = cursor.lastrowid
        conn.commit()
        return entry_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def search_user(search_query: str):
    """Find submission by username (case-insensitive)."""
    conn = sqlite3.connect("verifications.db")
    cursor = conn.cursor()
    # Strip @ if user included it
    clean_query = search_query.replace("@", "").strip().lower()
    
    cursor.execute(
        "SELECT entry_id, user_id, username, post_link, sol_address, photo_file_id, timestamp FROM submissions WHERE LOWER(username) = ?", 
        (clean_query,)
    )
    row = cursor.fetchone()
    conn.close()
    return row

def is_valid_url(url: str) -> bool:
    url_pattern = re.compile(r'^(https?://)([a-zA-Z0-9.-]+)(\.[a-zA-Z]{2,})(:\d+)?(/.*)?$')
    return bool(url_pattern.match(url))

def is_valid_solana_address(address: str) -> bool:
    if not (32 <= len(address) <= 44):
        return False
    try:
        decoded = base58.b58decode(address)
        return len(decoded) == 32
    except ValueError:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Welcome to the Giveaway!**\n\n"
        "Send your submission in one of these ways:\n"
        "1️⃣ **Text:** Send `<POST_LINK> <SOL_ADDRESS>`\n"
        "2️⃣ **Photo:** Send a screenshot of your post with your `<SOL_ADDRESS>` in the caption!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "NoUsername"
    
    if username == "NoUsername":
        await update.message.reply_text("❌ Please set a Telegram @username in your Telegram profile settings to enter.")
        return

    photo_file_id = None
    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
        text = (update.message.caption or "").strip()
    else:
        text = (update.message.text or "").strip()

    parts = text.split()

    if photo_file_id:
        if len(parts) == 1:
            sol_address = parts[0]
            post_link = "Screenshot Uploaded"
        elif len(parts) >= 2:
            post_link, sol_address = parts[0], parts[1]
        else:
            await update.message.reply_text("❌ Please send your SOL address in the photo caption.")
            return
    else:
        if len(parts) != 2:
            await update.message.reply_text("❌ Format error. Send: `<POST_LINK> <SOL_ADDRESS>`", parse_mode="Markdown")
            return
        post_link, sol_address = parts[0], parts[1]
        if not is_valid_url(post_link):
            await update.message.reply_text("❌ Invalid post link format.")
            return

    if not is_valid_solana_address(sol_address):
        await update.message.reply_text("❌ Invalid Solana wallet address.")
        return

    entry_id = save_submission(user_id, username, post_link, sol_address, photo_file_id)

    if not entry_id:
        await update.message.reply_text("⚠️ You have already entered this giveaway!")
        return

    await update.message.reply_text(
        f"✅ **Verification Saved!**\n\n"
        f"👤 **User:** @{username}\n"
        f"🔗 **Post:** {post_link}\n"
        f"👛 **SOL Address:** `{sol_address}`",
        parse_mode="Markdown"
    )

async def check_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: Send /winner @username to check details"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized access.")
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: `/winner @username` (e.g., `/winner @Buejoguede`)", parse_mode="Markdown")
        return

    search_query = context.args[0]
    row = search_user(search_query)

    if not row:
        await update.message.reply_text(f"❌ User **{search_query}** was not found in database.", parse_mode="Markdown")
        return

    entry_id, user_id, username, post_link, sol_address, photo_file_id, timestamp = row

    caption = (
        f"🎉 **WINNER DETAILS**\n\n"
        f"👤 **Username:** @{username} (ID: `{user_id}`)\n"
        f"👛 **SOL Address:** `{sol_address}`\n"
        f"🔗 **Proof/Link:** {post_link}\n"
        f"📅 **Submitted:** {timestamp}"
    )

    if photo_file_id:
        await update.message.reply_photo(photo=photo_file_id, caption=caption, parse_mode="Markdown")
    else:
        await update.message.reply_text(caption, parse_mode="Markdown")

if __name__ == "__main__":
    init_db()
    BOT_TOKEN = "8902673939:AAGf7YaL9dL_HFwwmV8ua-mt62NT8-SwkUg"

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("winner", check_winner))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_submission))

    print("Bot is running...")
    app.run_polling()
