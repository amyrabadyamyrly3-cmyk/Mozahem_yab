import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")

# 👑 چند ادمین (از Railway میاد)
ADMIN_IDS = os.getenv("ADMIN_ID", "0").split(",")

ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS if x.strip().isdigit()]

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


# ================= CHECK ADMIN =================
def is_admin(user_id):
    return user_id in ADMIN_IDS


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if uid not in data["users"]:
        data["users"][uid] = {"vip": False}
        save_data(data)

    keyboard = [
        ["🔍 جستجو شماره", "👤 جستجو اسم"],
        ["👤 حساب کاربری", "💎 VIP"],
        ["🆘 پشتیبانی"],
        ["➕ افزودن مشتری"]
    ]

    await update.message.reply_text(
        "👋 خوش آمدید",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# ================= MAIN =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    mode = context.user_data.get("mode")

    # ===== ADD CUSTOMER =====
    if text == "➕ افزودن مشتری":
        if not is_admin(uid):
            await update.message.reply_text("❌ فقط ادمین")
            return

        context.user_data["mode"] = "add"
        await update.message.reply_text("نام|شماره")
        return

    # ===== SEARCH PHONE =====
    if text == "🔍 جستجو شماره":
        context.user_data["mode"] = "phone"
        await update.message.reply_text("شماره را وارد کن")
        return

    # ===== SEARCH NAME =====
    if text == "👤 جستجو اسم":
        context.user_data["mode"] = "name"
        await update.message.reply_text("اسم را وارد کن")
        return

    # ===== VIP =====
    if text == "💎 VIP":
        for admin in ADMIN_IDS:
            await context.bot.send_message(admin, f"💎 VIP request: {uid}")
        await update.message.reply_text("ارسال شد")
        return

    # ===== ACCOUNT =====
    if text == "👤 حساب کاربری":
        user = data["users"].get(str(uid), {})
        await update.message.reply_text(
            f"ID: {uid}\nVIP: {user.get('vip', False)}"
        )
        return

    # ===== SUPPORT =====
    if text == "🆘 پشتیبانی":
        context.user_data["mode"] = "support"
        await update.message.reply_text("پیام خود را بنویس")
        return

    # ===== ADD CUSTOMER SAVE =====
    if mode == "add":
        if not is_admin(uid):
            await update.message.reply_text("❌ اجازه نداری")
            return

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
            await update.message.reply_text("فرمت: نام|شماره")
        return

    # ===== SEARCH PHONE =====
    if mode == "phone":
        for c in data["customers"].values():
            if c["phone"] == text:
                await update.message.reply_text(f"{c['name']} - {c['phone']}")
                return
        await update.message.reply_text("پیدا نشد")
        return

    # ===== SEARCH NAME =====
    if mode == "name":
        for c in data["customers"].values():
            if text in c["name"]:
                await update.message.reply_text(f"{c['name']} - {c['phone']}")
                return
        await update.message.reply_text("پیدا نشد")
        return

    # ===== SUPPORT =====
    if mode == "support":
        await context.bot.send_message(
            ADMIN_IDS[0],
            f"🆘 {uid}\n{text}"
        )
        await update.message.reply_text("ارسال شد")
        return


# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
