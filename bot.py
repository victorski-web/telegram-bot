import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Safely fetch environment variables and strip quotes/spaces
RAW_TOKEN = os.getenv("8902673939:AAGf7YaL9dL_HFwwmV8ua-mt62NT8-SwkUg", "")
BOT_TOKEN = RAW_TOKEN.strip().strip('"').strip("'")

RAW_ADMIN = os.getenv("7857565977", "0").strip().strip('"').strip("'")
ADMIN_ID = int(RAW_ADMIN) if RAW_ADMIN.isdigit() else 0

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN is missing or empty in Environment Variables!")

# KeepAlive Web Server
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
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN variable is completely missing from Render environment!")
        
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("winner", winner))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
