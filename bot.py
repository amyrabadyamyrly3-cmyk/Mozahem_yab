import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DATA_FILE = "data.json"


# ================= DATA =================
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"customers": {}, "users": {}}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
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
        ["🆘 دستیار همه‌کاره"],
        ["➕ افزودن مشتری"]
    ]

    await update.message.reply_text(
        "👋 به ربات خوش آمدید",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# ================= MAIN =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    mode = context.user_data.get("mode")

    # ========== ADMIN ADD ==========
    if text == "➕ افزودن مشتری":
        if uid != ADMIN_ID:
            await update.message.reply_text("❌ دسترسی نداری")
            return
        context.user_data["mode"] = "add"
        await update.message.reply_text("نام و شماره:\nنام|شماره")
        return

    # ========== SEARCH MODES ==========
    if text == "📞 جستجو با شماره":
        context.user_data["mode"] = "phone"
        await update.message.reply_text("شماره را وارد کن")
        return

    if text == "👤 جستجو با اسم":
        context.user_data["mode"] = "name"
        await update.message.reply_text("اسم را وارد کن")
        return

    # ========== VIP ==========
    if text == "💎 VIP":
        for admin in [ADMIN_ID]:
            await context.bot.send_message(admin, f"VIP request: {uid}")
        await update.message.reply_text("درخواست ارسال شد")
        return

    # ========== ACCOUNT ==========
    if text == "👤 حساب من":
        user = data["users"].get(str(uid), {})
        await update.message.reply_text(
            f"👤 ID: {uid}\n💎 VIP: {user.get('vip', False)}"
        )
        return

    # ========== SUPPORT ==========
    if text == "🆘 دستیار همه‌کاره":
        context.user_data["mode"] = "support"
        await update.message.reply_text("پیام خود را بنویس")
        return

    # ========== ADD CUSTOMER ==========
    if mode == "add":
        try:
            name, phone = text.split("|")
            cid = str(len(data["customers"]) + 1)

            data["customers"][cid] = {
                "name": name.strip(),
                "phone": phone.strip()
            }

            save_data(data)
            await update.message.reply_text("✅ اضافه شد")
        except:
            await update.message.reply_text("❌ فرمت: نام|شماره")
        return

    # ========== SEARCH PHONE ==========
    if mode == "phone":
        for c in data["customers"].values():
            if c["phone"] == text:
                await update.message.reply_text(f"👤 {c['name']}\n📞 {c['phone']}")
                return
        await update.message.reply_text("❌ پیدا نشد")
        return

    # ========== SEARCH NAME ==========
    if mode == "name":
        for c in data["customers"].values():
            if text in c["name"]:
                await update.message.reply_text(f"👤 {c['name']}\n📞 {c['phone']}")
                return
        await update.message.reply_text("❌ پیدا نشد")
        return

    # ========== SUPPORT ==========
    if mode == "support":
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆘 پیام:\n{uid}\n{text}"
        )
        await update.message.reply_text("ارسال شد")
        return


# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
