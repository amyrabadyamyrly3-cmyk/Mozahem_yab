import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===== TOKEN =====
TOKEN = os.getenv("BOT_TOKEN")

# ===== ADMIN =====
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DATA_FILE = "data.json"


# ===== LOAD/SAVE =====
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


# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📞 جستجو با شماره", "👤 جستجو با اسم"],
        ["➕ افزودن مشتری"],
        ["🆘 پشتیبانی"]
    ]

    await update.message.reply_text(
        "👋 به ربات خوش آمدید",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# ===== HANDLER =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    # ===== ADD CUSTOMER (ADMIN) =====
    if text == "➕ افزودن مشتری":
        if uid != ADMIN_ID:
            await update.message.reply_text("اجازه نداری ❌")
            return

        context.user_data["mode"] = "add"
        await update.message.reply_text("نام و شماره را اینطوری بفرست:\nنام|شماره")
        return

    # ===== SEARCH PHONE =====
    if text == "📞 جستجو با شماره":
        context.user_data["mode"] = "phone"
        await update.message.reply_text("شماره را وارد کن")
        return

    # ===== SEARCH NAME =====
    if text == "👤 جستجو با اسم":
        context.user_data["mode"] = "name"
        await update.message.reply_text("اسم را وارد کن")
        return

    # ===== SUPPORT =====
    if text == "🆘 پشتیبانی":
        context.user_data["mode"] = "support"
        await update.message.reply_text("پیام خود را بنویس")
        return

    mode = context.user_data.get("mode")

    # ===== ADD CUSTOMER SAVE =====
    if mode == "add":
        try:
            name, phone = text.split("|")
            cid = str(len(data["customers"]) + 1)

            data["customers"][cid] = {
                "name": name.strip(),
                "phone": phone.strip()
            }

            save_data(data)
            await update.message.reply_text("اضافه شد ✅")
        except:
            await update.message.reply_text("فرمت اشتباه ❌\nنام|شماره")
        return

    # ===== SEARCH PHONE =====
    if mode == "phone":
        for c in data["customers"].values():
            if c["phone"] == text:
                await update.message.reply_text(f"{c['name']} - {c['phone']}")
                return
        await update.message.reply_text("پیدا نشد ❌")
        return

    # ===== SEARCH NAME =====
    if mode == "name":
        for c in data["customers"].values():
            if text in c["name"]:
                await update.message.reply_text(f"{c['name']} - {c['phone']}")
                return
        await update.message.reply_text("پیدا نشد ❌")
        return

    # ===== SUPPORT =====
    if mode == "support":
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📩 پیام پشتیبانی:\n{uid}\n{text}"
        )
        await update.message.reply_text("ارسال شد ✅")
        return


# ===== MAIN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
