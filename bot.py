from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID
import database
import re
from datetime import datetime

# -------------------------
# 🎯 منوی اصلی
# -------------------------
def get_menu(user_id):
    keyboard = [
        ["🔎 استعلام هوشمند شماره", "👤 جستجوی کاربران"],
        ["👤 پروفایل من", "🎁 دعوت دوستان"],
        ["📦 بمبر تستی", "💎 عضویت VIP"],
        ["🆘 پشتیبانی"]
    ]

    if user_id == ADMIN_ID:
        keyboard.append(["👑 پنل مدیریت"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# -------------------------
# 🟢 استارت
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text(
        f"🛡 خوش آمدید {user.first_name}\nبه ربات مزاحم‌یاب حرفه‌ای",
        reply_markup=get_menu(user.id)
    )


# -------------------------
# 🧠 کنترل مرکزی (Router)
# -------------------------
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    user_id = user.id

    # -------------------------
    # 🔎 استعلام شماره (ورودی عددی)
    # -------------------------
    if re.fullmatch(r"09\d{9}", text):

        database.cursor.execute(
            "INSERT INTO logs (user_id, query, type, time) VALUES (?, ?, ?, ?)",
            (user_id, text, "number", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        database.conn.commit()

        await update.message.reply_text("❌ نتیجه‌ای پیدا نشد")

        # ارسال به ادمین
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 استعلام جدید\n👤 {user.full_name}\n📞 {text}"
        )
        return

    # -------------------------
    # 📌 منوی دکمه‌ها
    # -------------------------
    if text == "🔎 استعلام هوشمند شماره":
        await update.message.reply_text("📞 شماره مورد نظر را ارسال کنید:")
        return

    elif text == "👤 جستجوی کاربران":
        await update.message.reply_text("🔍 جستجوی کاربران فعال شد")
        return

    elif text == "👤 پروفایل من":
        await update.message.reply_text("👤 پروفایل شما در حال آماده‌سازی است")
        return

    elif text == "🎁 دعوت دوستان":
        await update.message.reply_text("🔗 لینک دعوت شما ساخته شد")
        return

    elif text == "📦 بمبر تستی":
        await update.message.reply_text("⏳ لطفاً شماره را وارد کنید\n(بزودی اجرا می‌شود)")
        return

    elif text == "💎 عضویت VIP":
        await update.message.reply_text("💎 بخش VIP در حال راه‌اندازی است")
        return

    elif text == "🆘 پشتیبانی":
        await update.message.reply_text("📩 پشتیبانی: به زودی آنلاین می‌شود")
        return

    elif text == "👑 پنل مدیریت" and user_id == ADMIN_ID:
        await update.message.reply_text("👑 ورود به پنل مدیریت")
        return

    # -------------------------
    # ❌ حالت پیش‌فرض
    # -------------------------
    await update.message.reply_text("❌ دستور نامعتبر است")


# -------------------------
# 🚀 اجرای ربات
# -------------------------
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

app.run_polling()
