import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Hardcoded Credentials
BOT_TOKEN = "8902673939:AAGhtm2I5_tPK7_4pwha0EhNNAV5wKz2_sE"
ADMIN_ID = 7857565977

# KeepAlive Web Server for Render
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")

    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# Database Setup
def init_db():
    conn = sqlite3.connect("verifications.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            x_link TEXT,
            sol_address TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Welcome to X-Confirmation Bot!**\n\n"
        "Please send your **X (Twitter) post link** and your **Solana (SOL) address** "
        "in a single message or separate messages to complete verification."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Text message handler (saves link and address to database)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    user_id = user.id
    username = user.username or f"user_{user_id}"

    conn = sqlite3.connect("verifications.db")
    c = conn.cursor()
    c.execute("SELECT x_link, sol_address FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()

    x_link = row[0] if row and row[0] else ""
    sol_address = row[1] if row and row[1] else ""

    # Simple check for X link vs SOL address
    if "x.com" in text.lower() or "twitter.com" in text.lower():
        x_link = text
    elif len(text) >= 32 and not text.startswith("http"):
        sol_address = text
    else:
        # If user sent both in one message or unstructured text
        parts = text.split()
        for part in parts:
            if "x.com" in part.lower() or "twitter.com" in part.lower():
                x_link = part
            elif len(part) >= 32 and not part.startswith("http"):
                sol_address = part

    # Save or update database
    c.execute("""
        INSERT INTO users (user_id, username, x_link, sol_address)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            x_link = CASE WHEN excluded.x_link != '' THEN excluded.x_link ELSE users.x_link END,
            sol_address = CASE WHEN excluded.sol_address != '' THEN excluded.sol_address ELSE users.sol_address END
    """, (user_id, username, x_link, sol_address))
    
    conn.commit()
    conn.close()

    response = "✅ **Details Received!**\n\n"
    if x_link:
        response += f"🔗 **X Link:** {x_link}\n"
    if sol_address:
        response += f"👛 **SOL Address:** `{sol_address}`\n"
    
    if not x_link or not sol_address:
        response += "\n⚠️ Please make sure you have sent *both* your X post link and SOL address."

    await update.message.reply_text(response, parse_mode="Markdown")

# /winner command handler
async def winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /winner @username")
        return

    target_username = context.args[0].replace("@", "").strip().lower()

    conn = sqlite3.connect("verifications.db")
    c = conn.cursor()
    c.execute("SELECT x_link, sol_address, username FROM users")
    rows = c.fetchall()
    conn.close()

    found = False
    for x_link, sol_address, db_username in rows:
        if db_username and db_username.replace("@", "").strip().lower() == target_username:
            found = True
            
            clean_address = str(sol_address).strip()
            clean_link = str(x_link).strip()
            
            msg = (
                f"🎉 <b>WINNER DETAILS</b> 🎉\n\n"
                f"👤 <b>User:</b> @{db_username}\n"
                f"🔗 <b>X Link:</b> {clean_link}\n"
                f"👛 <b>SOL Address:</b> <code>{clean_address}</code>"
            )
            await update.message.reply_text(msg, parse_mode="HTML")
            break

    if not found:
        await update.message.reply_text(f"❌ User @{target_username} not found in database.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add command and message handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("winner", winner))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
