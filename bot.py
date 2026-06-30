from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, REF_POINTS
import database
import re
from datetime import datetime


# ---------------- MENU ----------------
def menu(user_id):
    keyboard = [
        ["🔎 جستجو", "👤 پروفایل"],
        ["🎁 دعوت دوستان", "💎 VIP"],
        ["📦 بمبر", "🆘 پشتیبانی"]
    ]

    if user_id == ADMIN_ID:
        keyboard.append(["👑 پنل ادمین"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    database.cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, name, last_login)
    VALUES (?,?,?)
    """, (user.id, user.full_name, datetime.now().strftime("%Y-%m-%d %H:%M")))

    database.conn.commit()

    await update.message.reply_text(
        "🛡 ربات حرفه‌ای فعال شد",
        reply_markup=menu(user.id)
    )


# ---------------- HANDLER ----------------
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    uid = user.id


    # 🚫 BLOCK CHECK
    database.cursor.execute("SELECT blocked FROM users WHERE user_id=?", (uid,))
    b = database.cursor.fetchone()

    if b and b[0] == 1:
        await update.message.reply_text("⛔ شما مسدود شده‌اید")
        return


    # 🔎 SEARCH (NUMBER + NAME)
    if len(text) > 2:

        database.cursor.execute(
            "INSERT INTO logs (user_id, query, time) VALUES (?,?,?)",
            (uid, text, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )

        database.conn.commit()

        await update.message.reply_text("🔎 در حال بررسی...")

        return


    # ---------------- MENU ----------------
    if text == "🔎 جستجو":
        await update.message.reply_text("📩 شماره یا اسم را ارسال کنید")
        return

    if text == "👤 پروفایل":

        database.cursor.execute(
            "SELECT name, points, searches, vip FROM users WHERE user_id=?",
            (uid,)
        )

        data = database.cursor.fetchone()
        name, points, searches, vip = data if data else (user.full_name, 0, 0, 0)

        await update.message.reply_text(
            f"""👤 پروفایل

🧾 نام: {name}
⭐ امتیاز: {points}
🔎 جستجو: {searches}
💎 VIP: {'فعال' if vip else 'غیرفعال'}"""
        )
        return


    if text == "🎁 دعوت دوستان":
        bot_username = "YOUR_BOT_USERNAME"
        link = f"https://t.me/{bot_username}?start={uid}"

        await update.message.reply_text(f"🔗 لینک دعوت:\n{link}")
        return


    if text == "💎 VIP":
        await update.message.reply_text("📩 درخواست VIP ارسال شد")

        await context.bot.send_message(
            ADMIN_ID,
            f"💎 درخواست VIP\n👤 {user.full_name}\n🆔 {uid}"
        )
        return


    if text == "🆘 پشتیبانی":
        await update.message.reply_text("📩 پیام شما ثبت شد")
        return


    if text == "📦 بمبر":
        await update.message.reply_text("⏳ در حال پردازش")
        return


    # ---------------- ADMIN PANEL ----------------
    if text == "👑 پنل ادمین" and uid == ADMIN_ID:

        keyboard = [
            ["📊 آمار", "👥 کاربران"],
            ["🔎 لاگ‌ها", "🚫 بلاک کاربر"],
            ["📣 پیام همگانی", "🔙 خروج"]
        ]

        await update.message.reply_text(
            "👑 پنل ادمین فعال شد",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return


    # ---------------- ADMIN FUNCTIONS ----------------
    if uid == ADMIN_ID:

        if text == "📊 آمار":
            database.cursor.execute("SELECT COUNT(*) FROM users")
            users = database.cursor.fetchone()[0]

            database.cursor.execute("SELECT COUNT(*) FROM logs")
            logs = database.cursor.fetchone()[0]

            await update.message.reply_text(
                f"📊 آمار\n👥 کاربران: {users}\n🔎 جستجوها: {logs}"
            )
            return


        if text == "👥 کاربران":
            database.cursor.execute("SELECT user_id, name, last_login FROM users LIMIT 10")
            rows = database.cursor.fetchall()

            msg = "👥 کاربران:\n\n"

            for r in rows:
                msg += f"{r[0]} | {r[1]} | {r[2]}\n"

            await update.message.reply_text(msg)
            return


        if text == "🔎 لاگ‌ها":
            database.cursor.execute("""
            SELECT user_id, query, time FROM logs ORDER BY id DESC LIMIT 10
            """)
            rows = database.cursor.fetchall()

            msg = "🔎 لاگ‌ها:\n\n"

            for r in rows:
                msg += f"{r[0]} | {r[1]} | {r[2]}\n\n"

            await update.message.reply_text(msg)
            return


        if text.startswith("🚫 بلاک"):
            try:
                target = int(text.split(" ")[1])

                database.cursor.execute(
                    "UPDATE users SET blocked=1 WHERE user_id=?",
                    (target,)
                )
                database.conn.commit()

                await update.message.reply_text("⛔ کاربر بلاک شد")
            except:
                await update.message.reply_text("❌ فرمت: 🚫 بلاک 123456")
            return


        if text == "📣 پیام همگانی":
            await update.message.reply_text("✍ پیام را ارسال کنید")
            context.user_data["broadcast"] = True
            return


        if context.user_data.get("broadcast") and uid == ADMIN_ID:

            database.cursor.execute("SELECT user_id FROM users")
            users = database.cursor.fetchall()

            sent = 0

            for u in users:
                try:
                    await context.bot.send_message(u[0], text)
                    sent += 1
                except:
                    pass

            context.user_data["broadcast"] = False

            await update.message.reply_text(f"📣 ارسال شد به {sent} کاربر")
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
