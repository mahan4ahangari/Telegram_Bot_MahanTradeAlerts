import psycopg2
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")  # تو Render از Secret Env استفاده کن
OWNER_ID = 1039210853

# 📌 اتصال به PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")  # تو Render بعد از ساخت دیتابیس موجود است

def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# 📂 خواندن لیست کاربران فعال
def load_allowed_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, expire_time FROM allowed_users")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"user_id": r[0], "expire_time": r[1].strftime("%Y-%m-%d %H:%M:%S")} for r in rows]

# 💾 اضافه یا به‌روزرسانی کاربر
def save_or_update_user(user_id, expire_time):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO allowed_users (user_id, expire_time)
        VALUES (%s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET expire_time = EXCLUDED.expire_time
    """, (user_id, expire_time))
    conn.commit()
    cur.close()
    conn.close()

# ⏳ تبدیل رشته مدت زمان به timedelta
def parse_duration(duration_str):
    unit = duration_str[-1].lower()
    value = int(duration_str[:-1])
    if unit == "m": return timedelta(minutes=value)
    elif unit == "h": return timedelta(hours=value)
    elif unit == "d": return timedelta(days=value)
    else: raise ValueError("واحد زمان باید m, h یا d باشد.")

# 🚀 دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == OWNER_ID:
        await update.message.reply_text("سلام Owner! ربات همیشه در دسترس شماست.")
        return

    allowed_users = load_allowed_users()
    user_data = next((u for u in allowed_users if u["user_id"] == user_id), None)
    if not user_data:
        await update.message.reply_text("اشتراک شما شارژ نیست ❌️")
        return

    expire_time = datetime.strptime(user_data["expire_time"], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expire_time:
        await update.message.reply_text("مدت اشتراک شما به پایان رسیده ❌️")
        return

    await update.message.reply_text("ربات درحال تجزیه و تحلیل سیگنال ها است 🤖")

# ➕ دستور ادمین /adduser
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return

    try:
        new_id = int(context.args[0])
        duration = parse_duration(context.args[1])
    except:
        await update.message.reply_text("فرمت درست: /adduser <user_id> <مدت زمان مثل 30m, 2h, 3d>")
        return

    expire_time = (datetime.now() + duration).strftime("%Y-%m-%d %H:%M:%S")
    save_or_update_user(new_id, expire_time)

    await update.message.reply_text(f"✅ کاربر {new_id} اضافه شد تا {expire_time}")
    try:
        total_seconds = duration.total_seconds()
        approx = f"{int(total_seconds // 60)}m" if total_seconds < 3600 else \
                 f"{int(total_seconds // 3600)}h" if total_seconds < 86400 else \
                 f"{int(total_seconds // 86400)}d"
        await context.bot.send_message(chat_id=new_id, text=f"اکانت شما شارژ شد ✅️ مدت: {approx} تا {expire_time}")
    except:
        pass

# 📤 پیام Owner به تمام کاربران فعال
async def owner_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return

    allowed_users = load_allowed_users()
    now = datetime.now()
    for user in allowed_users:
        expire_time = datetime.strptime(user["expire_time"], "%Y-%m-%d %H:%M:%S")
        if now <= expire_time:
            try:
                await context.bot.send_message(chat_id=user["user_id"], text=update.message.text)
            except: pass

# ----------------- اجرای ربات -----------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("adduser", add_user))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, owner_broadcast))
    app.run_polling()
