from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, REF_POINTS
import database
import re
from datetime import datetime

# ---------------- MENU ----------------
def menu(user_id):
    keyboard = [
        ["🔎 استعلام شماره", "👤 جستجو"],
        ["👤 پروفایل من", "🎁 دعوت دوستان"],
        ["📦 بمبر", "💎 VIP"],
        ["🆘 پشتیبانی"]
    ]

    if user_id == ADMIN_ID:
        keyboard.append(["👑 پنل ادمین"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    database.cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, name) VALUES (?,?)",
        (user.id, user.full_name)
    )
    database.conn.commit()

    await update.message.reply_text(
        "🛡 ربات مزاحم‌یاب حرفه‌ای فعال شد",
        reply_markup=menu(user.id)
    )


# ---------------- ADMIN PANEL ----------------
async def open_admin_panel(update, context, user_id):

    admin_keyboard = [
        ["📊 آمار کلی", "👥 لیست کاربران"],
        ["🔎 لاگ جستجوها", "📣 پیام همگانی"],
        ["💎 مدیریت VIP", "🔙 خروج از پنل"]
    ]

    await update.message.reply_text(
        "👑 پنل ادمین حرفه‌ای فعال شد",
        reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
    )


# ---------------- CORE ----------------
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user

    # 🔎 استعلام شماره
    if re.fullmatch(r"09\d{9}", text):

        database.cursor.execute(
            "INSERT INTO logs (user_id, query, time) VALUES (?,?,?)",
            (user.id, text, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        database.conn.commit()

        database.cursor.execute(
            "UPDATE users SET searches = searches + 1 WHERE user_id=?",
            (user.id,)
        )
        database.conn.commit()

        await update.message.reply_text("❌ نتیجه‌ای پیدا نشد")

        await context.bot.send_message(
            ADMIN_ID,
            f"🔔 جستجو جدید\n👤 {user.full_name}\n📞 {text}"
        )
        return

    # ---------------- MENU ----------------
    if text == "🔎 استعلام شماره":
        await update.message.reply_text("📞 شماره را ارسال کنید")
        return

    elif text == "👤 جستجو":
        await update.message.reply_text("🔍 سیستم جستجو فعال است")
        return

    elif text == "👤 پروفایل من":

        database.cursor.execute(
            "SELECT name, points, searches, vip FROM users WHERE user_id=?",
            (user.id,)
        )
        data = database.cursor.fetchone()

        if data:
            name, points, searches, vip = data
        else:
            name, points, searches, vip = user.full_name, 0, 0, 0

        await update.message.reply_text(
            f"""👤 پروفایل شما

🧾 نام در ربات: {name}
⭐ امتیاز: {points}
🔎 جستجو: {searches}
💎 VIP: {'فعال' if vip else 'غیرفعال'}"""
        )
        return

    elif text == "🎁 دعوت دوستان":
        link = f"https://t.me/yourbot?start={user.id}"

        await update.message.reply_text(
            f"🔗 لینک دعوت شما:\n{link}\n\n➕ هر دعوت = {REF_POINTS} امتیاز"
        )
        return

    elif text == "💎 VIP":
        await update.message.reply_text("💎 بخش VIP فعال نیست")
        return

    elif text == "🆘 پشتیبانی":
        await update.message.reply_text("📩 پیام شما ثبت شد")
        return

    elif text == "📦 بمبر":
        await update.message.reply_text("⏳ در صف اجرا قرار گرفت")
        return

    # 👑 ADMIN ENTRY
    elif text == "👑 پنل ادمین" and user.id == ADMIN_ID:
        await open_admin_panel(update, context, user.id)
        return

    # ---------------- ADMIN ACTIONS ----------------
    if user.id == ADMIN_ID:

        if text == "📊 آمار کلی":
            database.cursor.execute("SELECT COUNT(*) FROM users")
            users = database.cursor.fetchone()[0]

            database.cursor.execute("SELECT COUNT(*) FROM logs")
            logs = database.cursor.fetchone()[0]

            await update.message.reply_text(
                f"📊 آمار سیستم\n\n👥 کاربران: {users}\n🔎 جستجوها: {logs}"
            )
            return

        elif text == "👥 لیست کاربران":
            database.cursor.execute("SELECT user_id, name, points FROM users LIMIT 10")
            rows = database.cursor.fetchall()

            msg = "👥 کاربران:\n\n"
            for r in rows:
                msg += f"🆔 {r[0]} | {r[1]} | ⭐ {r[2]}\n"

            await update.message.reply_text(msg)
            return

        elif text == "🔙 خروج از پنل":
            await update.message.reply_text(
                "🔙 خروج از پنل",
                reply_markup=menu(user.id)
            )
            return

    await update.message.reply_text("❌ دستور نامعتبر")


# ---------------- RUN ----------------
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

app.run_polling()
