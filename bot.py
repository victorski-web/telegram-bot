import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Hardcoded Credentials
BOT_TOKEN = "8902673939:AAGhtm2I5_tPK7_4pwha0EhNNAV5wKz2_sE"
ADMIN_ID = 7857565977

# KeepAlive Web Server to satisfy Render health checks
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")

    def log_message(self, format, *args):
        # Silence HTTP health check logs
        return

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    server.serve_forever()

# Start background web server
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
    
    # Permission Check
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
            
            # Formatted in HTML mode to prevent underscore crashes
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
    app.add_handler(CommandHandler("winner", winner))
    print("Bot is running...")
    # Clear old updates to resolve polling conflicts automatically
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
