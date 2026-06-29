import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "YOUR_BOT_TOKEN"

ADMINS = [123456789]  # آیدی خودت + ادمین دوم

DATA_FILE = "data.json"


# ================= DATA =================
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"customers": {}, "users": {}}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load_data()


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if uid not in data["users"]:
        data["users"][uid] = {"vip": False}

    save_data(data)

    keyboard = [
        ["📞 جستجو با شماره", "👤 جستجو با اسم"],
        ["👤 حساب من", "💎 VIP"],
        ["🆘 دستیار همه‌کاره"]
    ]

    await update.message.reply_text(
        "👋 به ربات خوش آمدید",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# ================= MAIN =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = str(update.effective_user.id)

    # ========== VIP ==========
    if text == "💎 VIP":
        for admin in ADMINS:
            await context.bot.send_message(
                admin,
                f"💎 درخواست VIP\nUser: {uid}"
            )
        await update.message.reply_text("📩 درخواست VIP ارسال شد")
        return

    # ========== Assistant ==========
    if text == "🆘 دستیار همه‌کاره":
        context.user_data["mode"] = "support"
        await update.message.reply_text("✍ پیام خود را بنویسید، ادمین پاسخ می‌دهد")
        return

    # ========== SEARCH MODE ==========
    if text == "📞 جستجو با شماره":
        context.user_data["mode"] = "phone"
        await update.message.reply_text("📞 شماره را وارد کنید")
        return

    if text == "👤 جستجو با اسم":
        context.user_data["mode"] = "name"
        await update.message.reply_text("👤 اسم را وارد کنید")
        return

    mode = context.user_data.get("mode")

    # ===== PHONE SEARCH =====
    if mode == "phone":
        for c in data["customers"].values():
            if c["phone"] == text:
                await update.message.reply_text(f"👤 {c['name']}\n📞 {c['phone']}")
                return
        await update.message.reply_text("❌ پیدا نشد")
        return

    # ===== NAME SEARCH =====
    if mode == "name":
        for c in data["customers"].values():
            if text in c["name"]:
                await update.message.reply_text(f"👤 {c['name']}\n📞 {c['phone']}")
                return
        await update.message.reply_text("❌ پیدا نشد")
        return

    # ===== SUPPORT =====
    if mode == "support":
        for admin in ADMINS:
            await context.bot.send_message(
                admin,
                f"🆘 پیام پشتیبانی\nUser: {uid}\n\n{text}"
            )
        await update.message.reply_text("📩 پیام ارسال شد")
        return


# ================= ADD CUSTOMER (ADMIN) =================
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return

    try:
        name, phone = update.message.text.split("|")
        cid = str(len(data["customers"]) + 1)

        data["customers"][cid] = {
            "name": name.strip(),
            "phone": phone.strip()
        }

        save_data(data)
        await update.message.reply_text("✅ اضافه شد")
    except:
        await update.message.reply_text("❌ فرمت: اسم|شماره")


# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add))

app.run_polling()
