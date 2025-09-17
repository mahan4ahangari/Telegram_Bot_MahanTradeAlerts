import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = "7842856740:AAHeNaZgSEhYZSUPJz_JjHoyNZ0Yp8RkpcY"
USERS_FILE = "py/signal tel project/allowed_users.json"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
OWNER_ID = 1039210853  # آیدی شما به عنوان Owner

# 📂 خواندن لیست کاربران
def load_allowed_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# 💾 ذخیره لیست کاربران
def save_allowed_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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
    
    # Owner همیشه فعال است
    if user_id == OWNER_ID:
        await update.message.reply_text("سلام Owner! ربات همیشه در دسترس شماست.")
        return

    allowed_users = load_allowed_users()
    user_data = next((u for u in allowed_users if u["user_id"] == user_id), None)

    if not user_data:
        await update.message.reply_text("اشتراک شما شارژ نیست ❌️ \n" \
        "لطفا برای شارژ کردن اکانت خود اقدام کنید")
        return

    expire_time = datetime.strptime(user_data["expire_time"], TIME_FORMAT)
    now = datetime.now()
    if now > expire_time:
        await update.message.reply_text("سلام رفیق مدت اشتراک شما به پایان رسیده لطفا برای تمدید اشتراک مجدد اقدام فرمایید \n"
                                        "با تشکر از حضورتان 💐")
        return

    message = (
        "ربات درحال تجزیه و تحلیل سیگنال ها است \n"
        " لطفا منتظر بمانید... 🤖"
    )
    await update.message.reply_text(message)

# ➕ دستور ادمین /adduser با پیام اطلاع‌رسانی و معادل زمانی
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return  # فقط Owner می‌تواند adduser بزند

    try:
        new_id = int(context.args[0])
        duration = parse_duration(context.args[1])
    except:
        await update.message.reply_text("فرمت درست: /adduser <user_id> <مدت زمان مثل 30m, 2h, 3d>")
        return

    expire_time = datetime.now() + duration
    allowed_users = load_allowed_users()
    allowed_users = [u for u in allowed_users if u["user_id"] != new_id]

    allowed_users.append({
        "user_id": new_id,
        "expire_time": expire_time.strftime(TIME_FORMAT)
    })
    save_allowed_users(allowed_users)

    # پیام تایید برای Owner
    await update.message.reply_text(f"✅ کاربر {new_id} اضافه شد.\n⏳ اعتبار تا: {expire_time}")

    # محاسبه معادل مدت زمان
    total_seconds = duration.total_seconds()
    if total_seconds < 3600:  # کمتر از 1 ساعت
        approx = f"{int(total_seconds // 60)}m"
    elif total_seconds < 86400:  # کمتر از 1 روز
        approx = f"{int(total_seconds // 3600)}h"
    else:
        approx = f"{int(total_seconds // 86400)}d"

    # پیام اطلاع‌رسانی برای کاربر اضافه شده
    try:
        await context.bot.send_message(
            chat_id=new_id,
            #text=f"🎉 سلام! اشتراک شما در ربات تا {expire_time} فعال شد. معادل {approx}"
            text= "سلام رفیق خوش آمدی 👋🏻 \n"
            "اکانت شما شارژ شد ✅️ \n"
            f"مدت اشتراک شما {approx} میباشد معادل {expire_time} \n"
            "در مدت اشتراک ربات سیگنال ها و تحلیل های دریافت شده را برای شما ارسال میکند \n"
            "مرسی که با من همراهی 🙏🏻🌹 \n"
            "لطفا منتظر بمانید ..."
        )
    except:
        pass

# 📤 پیام Owner به تمام کاربران فعال
async def owner_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return  # فقط Owner می‌تواند پیام‌ها را ارسال کند

    allowed_users = load_allowed_users()
    now = datetime.now()

    for user in allowed_users:
        expire_time = datetime.strptime(user["expire_time"], TIME_FORMAT)
        if now <= expire_time:  # فقط کاربران فعال
            try:
                await context.bot.send_message(chat_id=user["user_id"], text=update.message.text)
            except:
                pass  # اگر کاربر بلاک کرده یا مشکل داشت، رد کن

# ----------------- اجرای ربات -----------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("adduser", add_user))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, owner_broadcast))
    app.run_polling()
