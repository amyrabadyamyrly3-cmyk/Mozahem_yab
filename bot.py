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
        "🛡 ربات مزاحم‌یاب PRO MAX فعال شد",
        reply_markup=menu(user.id)
    )


# ---------------- MAIN HANDLER ----------------
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    uid = user.id

    # 🔎 SEARCH NUMBER
    if re.fullmatch(r"09\d{9}", text):

        database.cursor.execute(
            "INSERT INTO logs (user_id, query, time) VALUES (?,?,?)",
            (uid, text, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )

        database.cursor.execute(
            "UPDATE users SET searches = searches + 1 WHERE user_id=?",
            (uid,)
        )

        database.conn.commit()

        await update.message.reply_text("❌ نتیجه‌ای پیدا نشد")

        await context.bot.send_message(
            ADMIN_ID,
            f"🔔 جستجو جدید\n👤 {user.full_name}\n📞 {text}"
        )
        return

    # ---------------- USER MENU ----------------
    if text == "🔎 استعلام شماره":
        await update.message.reply_text("📞 شماره را ارسال کنید")
        return

    if text == "👤 جستجو":
        await update.message.reply_text("🔍 سیستم فعال است")
        return

    if text == "👤 پروفایل من":

        database.cursor.execute(
            "SELECT name, points, searches, vip FROM users WHERE user_id=?",
            (uid,)
        )
        data = database.cursor.fetchone()

        name, points, searches, vip = data if data else (user.full_name, 0, 0, 0)

        await update.message.reply_text(
            f"""👤 پروفایل PRO MAX

🧾 نام: {name}
⭐ امتیاز: {points}
🔎 جستجو: {searches}
💎 VIP: {'فعال' if vip else 'غیرفعال'}"""
        )
        return

    if text == "🎁 دعوت دوستان":
        link = f"https://t.me/yourbot?start={uid}"
        await update.message.reply_text(f"🔗 لینک دعوت:\n{link}")
        return

    if text == "💎 VIP":
        await update.message.reply_text("💎 VIP در حال توسعه است")
        return

    if text == "🆘 پشتیبانی":
        await update.message.reply_text("📩 پیام شما ثبت شد")
        return

    if text == "📦 بمبر":
        await update.message.reply_text("⏳ در صف اجرا")
        return

    # ---------------- ADMIN PANEL ----------------
    if text == "👑 پنل ادمین" and uid == ADMIN_ID:

        keyboard = [
            ["📊 آمار سیستم", "👥 لیست کاربران"],
            ["🔎 لاگ جستجو", "📣 پیام همگانی"],
            ["🔙 خروج"]
        ]

        await update.message.reply_text(
            "👑 پنل PRO MAX فعال شد",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    # ---------------- ADMIN FUNCTIONS ----------------
    if uid == ADMIN_ID:

        if text == "📊 آمار سیستم":
            database.cursor.execute("SELECT COUNT(*) FROM users")
            users = database.cursor.fetchone()[0]

            database.cursor.execute("SELECT COUNT(*) FROM logs")
            logs = database.cursor.fetchone()[0]

            await update.message.reply_text(
                f"📊 آمار سیستم\n👥 کاربران: {users}\n🔎 جستجو: {logs}"
            )
            return

        if text == "👥 لیست کاربران":
            database.cursor.execute("SELECT user_id, name FROM users LIMIT 10")
            rows = database.cursor.fetchall()

            msg = "👥 کاربران:\n\n"
            for r in rows:
                msg += f"{r[0]} | {r[1]}\n"

            await update.message.reply_text(msg)
            return

        if text == "🔎 لاگ جستجو":
            database.cursor.execute("""
            SELECT user_id, query, time FROM logs ORDER BY id DESC LIMIT 10
            """)
            rows = database.cursor.fetchall()

            msg = "🔎 لاگ سیستم:\n\n"
            for r in rows:
                msg += f"{r[0]} | {r[1]} | {r[2]}\n\n"

            await update.message.reply_text(msg)
            return

        if text == "📣 پیام همگانی":
            await update.message.reply_text("✍ پیام را ارسال کنید")
            context.user_data["broadcast"] = True
            return

        if context.user_data.get("broadcast") and uid == ADMIN_ID:

            database.cursor.execute("SELECT user_id FROM users")
            users = database.cursor.fetchall()

            success = 0

            for u in users:
                try:
                    await context.bot.send_message(u[0], text)
                    success += 1
                except:
                    pass

            context.user_data["broadcast"] = False

            await update.message.reply_text(f"📣 ارسال شد به {success} کاربر")
            return

        if text == "🔙 خروج":
            await update.message.reply_text(
                "🔙 خروج انجام شد",
                reply_markup=menu(uid)
            )
            return

    await update.message.reply_text("❌ دستور نامعتبر")


# ---------------- RUN ----------------
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

app.run_polling()
