import os
import psycopg2
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# ---- تنظیمات از Environment (برای Render) ----
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
DATABASE_URL = os.getenv("DATABASE_URL")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# 📂 اتصال به دیتابیس
def get_connection():
    return psycopg2.connect(DATABASE_URL)

# ⏳ تبدیل رشته مدت زمان به timedelta
def parse_duration(duration_str):
    unit = duration_str[-1].lower()
    value = int(duration_str[:-1])
    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    else:
        raise ValueError("واحد زمان باید m, h یا d باشد.")

# 🚀 دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == OWNER_ID:
        return await update.message.reply_text("سلام Owner! ربات همیشه در دسترس شماست.")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT expire_time FROM allowed_users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return await update.message.reply_text("اشتراک شما فعال نیست ❌ \nلطفا برای شارژ اقدام کنید.")

    expire_time = row[0]
    if datetime.now() > expire_time:
        return await update.message.reply_text("⏳ مدت اشتراک شما تمام شده است.\nبرای تمدید اقدام کنید.")

    await update.message.reply_text("ربات درحال تجزیه و تحلیل سیگنال‌هاست... 🤖")

# ➕ دستور /adduser
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    try:
        new_id = int(context.args[0])
        duration = parse_duration(context.args[1])
    except:
        return await update.message.reply_text("فرمت درست: /adduser <user_id> <مدت مثل 30m, 2h, 3d>")

    expire_time = datetime.now() + duration
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO allowed_users (user_id, expire_time) VALUES (%s, %s) "
        "ON CONFLICT (user_id) DO UPDATE SET expire_time = EXCLUDED.expire_time",
        (new_id, expire_time)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ کاربر {new_id} اضافه شد.\n⏳ اعتبار تا: {expire_time}")

    # اطلاع به کاربر
    try:
        await context.bot.send_message(
            chat_id=new_id,
            text=(
                "سلام رفیق 👋🏻\n"
                "اکانت شما شارژ شد ✅️ \n"
                f"مدت اشتراک شما تا {expire_time} فعال است.\n"
                "مرسی که با من همراهی 🙏🏻🌹"
            )
        )
    except:
        pass

# 📤 پیام Owner به همه کاربران فعال
async def owner_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, expire_time FROM allowed_users")
    users = cur.fetchall()
    conn.close()

    now = datetime.now()
    for uid, exp in users:
        if exp >= now:
            try:
                await context.bot.send_message(chat_id=uid, text=update.message.text)
            except:
                pass

# ----------------- اجرای ربات -----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("adduser", add_user))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, owner_broadcast))
    app.run_polling()

if __name__ == "__main__":
    main()
