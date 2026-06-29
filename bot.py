import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# ===== تنظیمات =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "TOKEN_خود_را_اینجا_بگذارید")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # آیدی عددی تلگرام خودت

# ===== وضعیت‌های مکالمه =====
WAITING_FOR_ADD_NAME = 1
WAITING_FOR_ADD_PHONE = 2
WAITING_FOR_DELETE = 3

# ===== دیتابیس =====
def init_db():
    conn = sqlite3.connect("customers.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def search_by_name(name):
    conn = sqlite3.connect("customers.db")
    c = conn.cursor()
    c.execute("SELECT name, phone FROM customers WHERE name = ?", (name,))
    results = c.fetchall()
    conn.close()
    return results

def search_by_phone(phone):
    conn = sqlite3.connect("customers.db")
    c = conn.cursor()
    c.execute("SELECT name, phone FROM customers WHERE phone LIKE ?", (f"%{phone}%",))
    results = c.fetchall()
    conn.close()
    return results

def add_customer(name, phone):
    conn = sqlite3.connect("customers.db")
    c = conn.cursor()
    c.execute("INSERT INTO customers (name, phone) VALUES (?, ?)", (name, phone))
    conn.commit()
    conn.close()

def delete_customer(phone):
    conn = sqlite3.connect("customers.db")
    c = conn.cursor()
    c.execute("DELETE FROM customers WHERE phone = ?", (phone,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected

def get_all_customers():
    conn = sqlite3.connect("customers.db")
    c = conn.cursor()
    c.execute("SELECT name, phone FROM customers ORDER BY name")
    results = c.fetchall()
    conn.close()
    return results

# ===== منوها =====
def main_keyboard(is_admin=False):
    buttons = [
        [KeyboardButton("🔍 جستجو با اسم"), KeyboardButton("📞 جستجو با شماره")],
    ]
    if is_admin:
        buttons.append([KeyboardButton("➕ افزودن مشتری"), KeyboardButton("🗑 حذف مشتری")])
        buttons.append([KeyboardButton("📋 لیست همه مشتریان")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ===== هندلرها =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_ID
    name = update.effective_user.first_name

    if is_admin:
        msg = f"👋 سلام {name} عزیز!\n\n🔐 شما به عنوان **ادمین** وارد شدید.\n\nاز منوی زیر استفاده کنید:"
    else:
        msg = f"👋 سلام {name} عزیز!\n\n🛍 به ربات شاپ خوش آمدید.\n\nمی‌توانید با اسم یا شماره جستجو کنید:"

    await update.message.reply_text(msg, reply_markup=main_keyboard(is_admin), parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_ID

    # ===== جستجو با اسم =====
    if text == "🔍 جستجو با اسم":
        context.user_data["mode"] = "search_name"
        await update.message.reply_text("✏️ لطفاً اسم مشتری را بنویسید:")
        return

    # ===== جستجو با شماره =====
    if text == "📞 جستجو با شماره":
    context.user_data["mode"] = "search_phone"
    await update.message.reply_text(
        "📞 جستجو با شماره\n\n"
        "لطفاً شماره را به صورت کامل وارد کنید\n\n"
        "❗ مثال درست:\n"
        "09123456789\n\n"
        "❌ مثال اشتباه:\n"
        "9123456789\n"
        "09\n"
        "+98 912 345 6789"
    )
    return

    # ===== افزودن مشتری (فقط ادمین) =====
    if text == "➕ افزودن مشتری":
        if not is_admin:
            await update.message.reply_text("⛔ شما دسترسی ندارید.")
            return
        context.user_data["mode"] = "add_name"
        await update.message.reply_text("✏️ اسم و فامیل مشتری جدید را بنویسید:")
        return

    # ===== حذف مشتری (فقط ادمین) =====
    if text == "🗑 حذف مشتری":
        if not is_admin:
            await update.message.reply_text("⛔ شما دسترسی ندارید.")
            return
        context.user_data["mode"] = "delete"
        await update.message.reply_text("✏️ شماره تلفن مشتری که می‌خواهید حذف کنید را بنویسید:")
        return

    # ===== لیست همه (فقط ادمین) =====
    if text == "📋 لیست همه مشتریان":
        if not is_admin:
            await update.message.reply_text("⛔ شما دسترسی ندارید.")
            return
        customers = get_all_customers()
        if not customers:
            await update.message.reply_text("📭 هیچ مشتری‌ای ثبت نشده.")
            return
        msg = f"📋 *لیست همه مشتریان ({len(customers)} نفر):*\n\n"
        for i, (name, phone) in enumerate(customers, 1):
            msg += f"{i}. 👤 {name}\n   📞 {phone}\n\n"
        # تقسیم پیام اگر طولانی بود
        if len(msg) > 4000:
            chunks = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # ===== پردازش ورودی‌ها =====
    mode = context.user_data.get("mode")

    if mode == "search_name":
        results = search_by_name(text)
        context.user_data["mode"] = None
        if results:
            msg = f"🔍 نتایج جستجو برای «{text}»:\n\n"
            for name, phone in results:
                msg += f"👤 {name}\n📞 {phone}\n\n"
        else:
            msg = f"❌ هیچ مشتری‌ای با اسم «{text}» پیدا نشد."
        await update.message.reply_text(msg)

    elif mode == "search_phone":
        results = search_by_phone(text)
        context.user_data["mode"] = None
        if results:
            msg = f"🔍 نتایج جستجو برای «{text}»:\n\n"
            for name, phone in results:
                msg += f"👤 {name}\n📞 {phone}\n\n"
        else:
            msg = f"❌ هیچ مشتری‌ای با شماره «{text}» پیدا نشد."
        await update.message.reply_text(msg)

    elif mode == "add_name" and is_admin:
        context.user_data["new_customer_name"] = text
        context.user_data["mode"] = "add_phone"
        await update.message.reply_text(f"✅ اسم: *{text}*\n\nحالا شماره تلفن را بنویسید:", parse_mode="Markdown")

    elif mode == "add_phone" and is_admin:
        name = context.user_data.get("new_customer_name")
        phone = text
        add_customer(name, phone)
        context.user_data["mode"] = None
        context.user_data["new_customer_name"] = None
        await update.message.reply_text(
            f"✅ مشتری جدید اضافه شد!\n\n👤 {name}\n📞 {phone}",
            reply_markup=main_keyboard(is_admin)
        )

    elif mode == "delete" and is_admin:
        affected = delete_customer(text)
        context.user_data["mode"] = None
        if affected:
            await update.message.reply_text(f"✅ مشتری با شماره {text} حذف شد.")
        else:
            await update.message.reply_text(f"❌ هیچ مشتری‌ای با شماره {text} پیدا نشد.")

    else:
        await update.message.reply_text(
            "لطفاً از دکمه‌های منو استفاده کنید 👇",
            reply_markup=main_keyboard(is_admin)
        )

# ===== اجرا =====
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ ربات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()
