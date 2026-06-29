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


# ================= START MENU =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if uid not in data["users"]:
        data["users"][uid] = {"vip": False}
        save_data(data)

    keyboard = [
        ["🔎 جستجوی شماره", "👤 جستجوی نام"],
        ["👤 حساب کاربری", "💎 درخواست VIP"],
        ["🆘 پشتیبانی هوشمند"],
        ["➕ پنل ادمین"]
    ]

    await update.message.reply_text(
        "🌟 به پنل حرفه‌ای مدیریت مشتری خوش آمدید\n\n"
        "🔹 یک گزینه انتخاب کنید:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# ================= MAIN HANDLER =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    mode = context.user_data.get("mode")

    # ================= ADMIN PANEL =================
    if text == "➕ پنل ادمین":
        if uid != ADMIN_ID:
            await update.message.reply_text("⛔ فقط ادمین")
            return

        keyboard = [
            ["➕ افزودن تکی"],
            ["📋 افزودن چندتایی"],
            ["📊 لیست مشتری‌ها"]
        ]

        await update.message.reply_text(
            "👑 پنل ادمین فعال شد",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    # ================= ADD SINGLE =================
    if text == "➕ افزودن تکی":
        if uid != ADMIN_ID:
            return

        context.user_data["mode"] = "add_single"
        await update.message.reply_text("نام|شماره را وارد کن")
        return

    # ================= ADD BULK =================
    if text == "📋 افزودن چندتایی":
        if uid != ADMIN_ID:
            return

        context.user_data["mode"] = "add_bulk"
        await update.message.reply_text(
            "📋 چندتایی اضافه کن\n\n"
            "هر خط:\n"
            "نام|شماره\n\n"
            "مثال:\n"
            "علی|0912\nرضا|0935"
        )
        return

    # ================= LIST CUSTOMERS =================
    if text == "📊 لیست مشتری‌ها":
        if uid != ADMIN_ID:
            return

        if not data["customers"]:
            await update.message.reply_text("خالیه")
            return

        msg = "📊 لیست مشتری‌ها:\n\n"
        for c in data["customers"].values():
            msg += f"{c['name']} - {c['phone']}\n"

        await update.message.reply_text(msg)
        return

    # ================= SEARCH PHONE =================
    if text == "🔎 جستجوی شماره":
        context.user_data["mode"] = "phone"
        await update.message.reply_text("شماره را وارد کن")
        return

    # ================= SEARCH NAME =================
    if text == "👤 جستجوی نام":
        context.user_data["mode"] = "name"
        await update.message.reply_text("نام را وارد کن")
        return

    # ================= VIP =================
    if text == "💎 درخواست VIP":
        await context.bot.send_message(
            ADMIN_ID,
            f"💎 درخواست VIP\n👤 {uid}"
        )
        await update.message.reply_text("ارسال شد")
        return

    # ================= ACCOUNT =================
    if text == "👤 حساب کاربری":
        user = data["users"].get(str(uid), {})
        await update.message.reply_text(
            f"👤 حساب شما\n\nID: {uid}\nVIP: {user.get('vip', False)}"
        )
        return

    # ================= SUPPORT =================
    if text == "🆘 پشتیبانی هوشمند":
        context.user_data["mode"] = "support"
        await update.message.reply_text("پیام خود را بنویس")
        return

    # ================= ADD SINGLE SAVE =================
    if mode == "add_single":
        if uid != ADMIN_ID:
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

    # ================= BULK ADD =================
    if mode == "add_bulk":
        if uid != ADMIN_ID:
            return

        lines = text.split("\n")
        for line in lines:
            try:
                name, phone = line.split("|")
                cid = str(len(data["customers"]) + 1)

                data["customers"][cid] = {
                    "name": name.strip(),
                    "phone": phone.strip()
                }
            except:
                continue

        save_data(data)
        await update.message.reply_text("✅ همه اضافه شدند")
        return

    # ================= SEARCH PHONE =================
    if mode == "phone":
        for c in data["customers"].values():
            if c["phone"] == text:
                await update.message.reply_text(f"{c['name']} - {c['phone']}")
                return
        await update.message.reply_text("پیدا نشد")
        return

    # ================= SEARCH NAME =================
    if mode == "name":
        for c in data["customers"].values():
            if text in c["name"]:
                await update.message.reply_text(f"{c['name']} - {c['phone']}")
                return
        await update.message.reply_text("پیدا نشد")
        return

    # ================= SUPPORT =================
    if mode == "support":
        await context.bot.send_message(
            ADMIN_ID,
            f"🆘 پیام:\n{uid}\n{text}"
        )
        await update.message.reply_text("ارسال شد")
        return


# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
