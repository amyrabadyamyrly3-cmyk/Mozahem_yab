from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID
import database
import re
from datetime import datetime

# 🔹 منو
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


# 🔹 استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 به ربات مزاحم‌یاب حرفه‌ای خوش آمدید",
        reply_markup=get_menu(update.effective_user.id)
    )


# 🔹 مدیریت پیام‌ها
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user

    # 🔎 جستجوی شماره
    if re.fullmatch(r"09\d{9}", text):

        database.cursor.execute(
            "INSERT INTO logs (user_id, query, type, time) VALUES (?, ?, ?, ?)",
            (user.id, text, "number", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        database.conn.commit()

        await update.message.reply_text("❌ نتیجه‌ای پیدا نشد")

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 جستجوی جدید\n👤 {user.full_name}\n📞 {text}"
        )
        return

    await update.message.reply_text("❌ دستور نامعتبر")


# 🔹 اجرای ربات
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

app.run_polling()
