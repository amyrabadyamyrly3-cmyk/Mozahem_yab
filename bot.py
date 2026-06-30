import os
import re
import json
import random
import string
from datetime import datetime, timedelta

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATA_FILE = "data.json"

PHONE_RE = re.compile(r"^09\d{9}$")
BIRTHDAY_RE = re.compile(r"^\d{2}-\d{2}$")  # MM-DD


# ================= DATA =================
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d.setdefault("customers", {})   # cid -> {name, phone}
    d.setdefault("users", {})       # uid(str) -> {points, vip, ref_code, referred_by,
                                     #              name, phone, birthday, last_active}
    d.setdefault("relay", {})       # sent_message_id(str) -> user_id(int)
    return d


def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


data = load_data()


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def get_user(uid):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {
            "points": 0,
            "vip": False,
            "ref_code": uid,
            "referred_by": None,
            "name": None,
            "phone": None,
            "birthday": None,
            "last_active": now_str(),
        }
        save_data(data)
    return data["users"][uid]


def touch_user(uid):
    u = get_user(uid)
    u["last_active"] = now_str()
    save_data(data)


# ================= KEYBOARDS =================
def main_keyboard():
    return ReplyKeyboardMarkup([
        ["🔍 جستجو با شماره", "👤 جستجو با نام"],
        ["🛒 ثبت درخواست خرید", "🆘 پشتیبانی"],
        ["💳 حساب من", "🎁 دعوت از دوستان"],
        ["📦 بمبر"],
    ], resize_keyboard=True)


def exit_keyboard():
    return ReplyKeyboardMarkup([["🔙 خروج به منو"]], resize_keyboard=True)


def admin_keyboard():
    return ReplyKeyboardMarkup([
        ["➕ افزودن مشتری تکی", "📋 افزودن مشتری گروهی"],
        ["✏️ ویرایش مشتری", "🗑 حذف مشتری"],
        ["📊 آمار فروش", "📤 خروجی لیست"],
        ["👥 کاربران ربات", "🎂 تغییر تاریخ تولد"],
        ["💬 پیام به کاربر خاص", "📢 پیام همگانی"],
        ["🔙 خروج به منو"],
    ], resize_keyboard=True)


def is_admin(uid):
    return uid == ADMIN_ID


def clear_mode(context):
    context.user_data["mode"] = None


# ================= NOTIFY ADMIN =================
async def notify_admin(context, text):
    try:
        await context.bot.send_message(ADMIN_ID, text)
    except Exception:
        pass


async def notify_admin_search(context, user, kind, query, found):
    name = user.first_name or "بدون نام"
    uid = user.id
    msg = (
        f"🔔 جستجوی جدید\n\n"
        f"👤 کاربر: {name} (آیدی: {uid})\n"
        f"🔍 نوع: {kind}\n"
        f"📝 متن: {query}\n"
        f"✅ نتیجه: {'پیدا شد' if found else 'پیدا نشد'}\n"
        f"🕐 زمان: {now_str()}"
    )
    await notify_admin(context, msg)


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = get_user(uid)
    touch_user(uid)

    # referral handling: /start <referrer_uid>
    if context.args:
        ref_code = context.args[0]
        if ref_code != str(uid) and u["referred_by"] is None:
            if ref_code in data["users"]:
                u["referred_by"] = ref_code
                u["points"] += 20
                data["users"][ref_code]["points"] += 20
                save_data(data)
                await context.bot.send_message(
                    int(ref_code),
                    "🎁 یک دوست با کد دعوت شما عضو شد! ۲۰ امتیاز گرفتید."
                )

    clear_mode(context)
    name = update.effective_user.first_name or ""
    await update.message.reply_text(
        f"👋 سلام {name} عزیز!\n\n"
        f"🌟 به ربات شاپ ما خوش آمدید\n"
        f"🔹 یک گزینه را انتخاب کنید:",
        reply_markup=main_keyboard()
    )


# ================= ADMIN ENTRY (command only) =================
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    clear_mode(context)
    await update.message.reply_text("👑 پنل مدیریت فعال شد", reply_markup=admin_keyboard())


# ================= MAIN HANDLER =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    user_obj = update.effective_user
    touch_user(uid)

    # ---- Admin relay: reply to a forwarded message ----
    if is_admin(uid) and update.message.reply_to_message:
        rid = str(update.message.reply_to_message.message_id)
        if rid in data["relay"]:
            target = data["relay"][rid]
            try:
                await context.bot.send_message(target, f"💬 پاسخ ادمین:\n\n{text}")
                await update.message.reply_text("✅ پیام ارسال شد.")
            except Exception:
                await update.message.reply_text("❌ ارسال نشد.")
            return

    mode = context.user_data.get("mode")

    # ---- universal exit ----
    if text == "🔙 خروج به منو":
        clear_mode(context)
        if is_admin(uid):
            await update.message.reply_text("بازگشت به پنل مدیریت", reply_markup=admin_keyboard())
        else:
            await update.message.reply_text("بازگشت به منوی اصلی", reply_markup=main_keyboard())
        return

    # ============ CUSTOMER MENU BUTTONS ============
    if text == "🔍 جستجو با شماره":
        context.user_data["mode"] = "search_phone"
        await update.message.reply_text("📞 شماره تلفن مورد نظر را وارد کنید:", reply_markup=exit_keyboard())
        return

    if text == "👤 جستجو با نام":
        context.user_data["mode"] = "search_name"
        await update.message.reply_text("👤 نام و فامیل مورد نظر را وارد کنید:", reply_markup=exit_keyboard())
        return

    if text == "🛒 ثبت درخواست خرید":
        context.user_data["mode"] = "buy_request"
        await update.message.reply_text("🛒 درخواست خرید خود را بنویسید:", reply_markup=exit_keyboard())
        return

    if text == "🆘 پشتیبانی":
        context.user_data["mode"] = "support"
        await update.message.reply_text("🆘 پیام خود را برای پشتیبانی بنویسید:", reply_markup=exit_keyboard())
        return

    if text == "💳 حساب من":
        u = get_user(uid)
        bday = u["birthday"] or "ثبت نشده"
        await update.message.reply_text(
            f"💳 حساب کاربری شما\n\n"
            f"🆔 آیدی: {uid}\n"
            f"⭐ امتیاز: {u['points']}\n"
            f"👑 وضعیت VIP: {'بله ✅' if u['vip'] else 'خیر'}\n"
            f"🎂 تاریخ تولد: {bday}\n\n"
            f"برای ثبت/تغییر تاریخ تولد (فرمت ماه-روز مثل 07-25) همینجا بفرستید:"
        )
        context.user_data["mode"] = "set_birthday"
        return

    if text == "🎁 دعوت از دوستان":
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={uid}"
        await update.message.reply_text(
            "🎁 دوستان خود را دعوت کنید!\n\n"
            f"🔗 لینک دعوت شما:\n{link}\n\n"
            "✨ با هر دعوت موفق، شما و دوستتان هر دو ۲۰ امتیاز می‌گیرید."
        )
        return

    if text == "📦 بمبر":
        context.user_data["mode"] = "bomber_phone"
        await update.message.reply_text(
            "📦 شماره تلفن خود را وارد کنید\n\n"
            "فرمت صحیح: 09127654123",
            reply_markup=exit_keyboard()
        )
        return

    # ============ ADMIN MENU BUTTONS ============
    if is_admin(uid):
        if text == "➕ افزودن مشتری تکی":
            context.user_data["mode"] = "admin_add_name"
            await update.message.reply_text("👤 نام و فامیل مشتری جدید را بنویسید:", reply_markup=exit_keyboard())
            return

        if text == "📋 افزودن مشتری گروهی":
            context.user_data["mode"] = "admin_add_bulk"
            await update.message.reply_text(
                "📋 هر خط را به شکل زیر بنویسید:\nنام|شماره\n\nمثال:\nعلی رضایی|09120000000\nسارا احمدی|09130000000",
                reply_markup=exit_keyboard()
            )
            return

        if text == "✏️ ویرایش مشتری":
            context.user_data["mode"] = "admin_edit_find"
            await update.message.reply_text("📞 شماره مشتری که می‌خواهید ویرایش کنید را بفرستید:", reply_markup=exit_keyboard())
            return

        if text == "🗑 حذف مشتری":
            context.user_data["mode"] = "admin_delete"
            await update.message.reply_text("📞 شماره مشتری که می‌خواهید حذف کنید را بفرستید:", reply_markup=exit_keyboard())
            return

        if text == "📊 آمار فروش":
            customers = data["customers"]
            total = len(customers)
            await update.message.reply_text(
                f"📊 آمار فروش\n\n👥 تعداد کل مشتریان: {total}\n"
                f"👤 تعداد کاربران ربات: {len(data['users'])}"
            )
            return

        if text == "📤 خروجی لیست":
            customers = data["customers"]
            if not customers:
                await update.message.reply_text("📭 لیست خالی است.")
                return
            lines = [f"{c['name']} - {c['phone']}" for c in customers.values()]
            content = "\n".join(lines)
            with open("export.txt", "w", encoding="utf-8") as f:
                f.write(content)
            await update.message.reply_document(document=open("export.txt", "rb"), filename="مشتریان.txt")
            return

        if text == "👥 کاربران ربات":
            if not data["users"]:
                await update.message.reply_text("کاربری ثبت نشده.")
                return
            msg = "👥 کاربران ربات:\n\n"
            for uid_str, u in data["users"].items():
                nm = u.get("name") or "بدون نام"
                msg += f"🆔 {uid_str} - {nm} - ⭐{u['points']}\n"
            msg += "\n✏️ برای ثبت اسم: آیدی کاربر را بفرستید."
            context.user_data["mode"] = "admin_set_user_name_id"
            await update.message.reply_text(msg[:4000], reply_markup=exit_keyboard())
            return

        if text == "🎂 تغییر تاریخ تولد":
            context.user_data["mode"] = "admin_birthday_id"
            await update.message.reply_text("🆔 آیدی عددی کاربر را بفرستید:", reply_markup=exit_keyboard())
            return

        if text == "💬 پیام به کاربر خاص":
            context.user_data["mode"] = "admin_msg_user_id"
            await update.message.reply_text("🆔 آیدی عددی کاربر را بفرستید:", reply_markup=exit_keyboard())
            return

        if text == "📢 پیام همگانی":
            context.user_data["mode"] = "admin_broadcast"
            await update.message.reply_text("📢 متن پیام همگانی را بنویسید:", reply_markup=exit_keyboard())
            return

    # ============ MODE PROCESSING ============

    if mode == "search_phone":
        clear_mode(context)
        found_c = None
        for c in data["customers"].values():
            if c["phone"] == text:
                found_c = c
                break
        await notify_admin_search(context, user_obj, "شماره", text, bool(found_c))
        if found_c:
            await update.message.reply_text(f"✅ {found_c['name']} - {found_c['phone']}", reply_markup=main_keyboard())
        else:
            await update.message.reply_text("❌ مشتری‌ای با این شماره پیدا نشد.", reply_markup=main_keyboard())
        return

    if mode == "search_name":
        clear_mode(context)
        found_c = None
        for c in data["customers"].values():
            if c["name"] == text:
                found_c = c
                break
        await notify_admin_search(context, user_obj, "نام", text, bool(found_c))
        if found_c:
            await update.message.reply_text(f"✅ {found_c['name']} - {found_c['phone']}", reply_markup=main_keyboard())
        else:
            await update.message.reply_text("❌ مشتری‌ای با این نام پیدا نشد.", reply_markup=main_keyboard())
        return

    if mode == "buy_request":
        clear_mode(context)
        sent = await context.bot.send_message(
            ADMIN_ID,
            f"🛒 درخواست خرید جدید\n👤 {user_obj.first_name} (آیدی: {uid})\n\n📝 {text}"
        )
        data["relay"][str(sent.message_id)] = uid
        save_data(data)
        await update.message.reply_text("✅ درخواست شما ارسال شد. به‌زودی پاسخ می‌گیرید.", reply_markup=main_keyboard())
        return

    if mode == "support":
        clear_mode(context)
        sent = await context.bot.send_message(
            ADMIN_ID,
            f"🆘 پیام پشتیبانی\n👤 {user_obj.first_name} (آیدی: {uid})\n\n📝 {text}"
        )
        data["relay"][str(sent.message_id)] = uid
        save_data(data)
        await update.message.reply_text("✅ پیام شما ارسال شد.", reply_markup=main_keyboard())
        return

    if mode == "set_birthday":
        clear_mode(context)
        if BIRTHDAY_RE.match(text):
            get_user(uid)["birthday"] = text
            save_data(data)
            await update.message.reply_text("✅ تاریخ تولد ثبت شد.", reply_markup=main_keyboard())
        else:
            await update.message.reply_text("❌ فرمت اشتباه است. مثال صحیح: 07-25", reply_markup=main_keyboard())
        return

    if mode == "bomber_phone":
        if PHONE_RE.match(text):
            clear_mode(context)
            get_user(uid)["phone"] = text
            save_data(data)
            await notify_admin(context, f"📦 بمبر - شماره جدید\n👤 {user_obj.first_name} (آیدی: {uid})\n📞 {text}")
            await update.message.reply_text("✅ شماره شما با موفقیت ارسال شد.", reply_markup=main_keyboard())
        else:
            await update.message.reply_text(
                "❌ شماره وارد شده اشتباه است.\nفرمت صحیح: 09127654123",
                reply_markup=exit_keyboard()
            )
        return

    # ============ ADMIN MODE PROCESSING ============
    if is_admin(uid):
        if mode == "admin_add_name":
            context.user_data["new_name"] = text
            context.user_data["mode"] = "admin_add_phone"
            await update.message.reply_text("📞 شماره تلفن را بفرستید:", reply_markup=exit_keyboard())
            return

        if mode == "admin_add_phone":
            name = context.user_data.get("new_name", "")
            cid = str(len(data["customers"]) + 1)
            data["customers"][cid] = {"name": name, "phone": text}
            save_data(data)
            clear_mode(context)
            await update.message.reply_text(f"✅ مشتری اضافه شد:\n{name} - {text}", reply_markup=admin_keyboard())
            return

        if mode == "admin_add_bulk":
            clear_mode(context)
            count = 0
            for line in text.split("\n"):
                if "|" in line:
                    nm, ph = line.split("|", 1)
                    cid = str(len(data["customers"]) + 1)
                    data["customers"][cid] = {"name": nm.strip(), "phone": ph.strip()}
                    count += 1
            save_data(data)
            await update.message.reply_text(f"✅ {count} مشتری اضافه شد.", reply_markup=admin_keyboard())
            return

        if mode == "admin_edit_find":
            target_cid = None
            for cid, c in data["customers"].items():
                if c["phone"] == text:
                    target_cid = cid
                    break
            if target_cid:
                context.user_data["edit_cid"] = target_cid
                context.user_data["mode"] = "admin_edit_name"
                await update.message.reply_text("👤 نام جدید را بفرستید:", reply_markup=exit_keyboard())
            else:
                await update.message.reply_text("❌ مشتری پیدا نشد.", reply_markup=admin_keyboard())
                clear_mode(context)
            return

        if mode == "admin_edit_name":
            context.user_data["edit_name"] = text
            context.user_data["mode"] = "admin_edit_phone"
            await update.message.reply_text("📞 شماره جدید را بفرستید:", reply_markup=exit_keyboard())
            return

        if mode == "admin_edit_phone":
            cid = context.user_data.get("edit_cid")
            if cid in data["customers"]:
                data["customers"][cid] = {"name": context.user_data.get("edit_name"), "phone": text}
                save_data(data)
                await update.message.reply_text("✅ ویرایش شد.", reply_markup=admin_keyboard())
            else:
                await update.message.reply_text("❌ خطا در ویرایش.", reply_markup=admin_keyboard())
            clear_mode(context)
            return

        if mode == "admin_delete":
            clear_mode(context)
            target_cid = None
            for cid, c in data["customers"].items():
                if c["phone"] == text:
                    target_cid = cid
                    break
            if target_cid:
                del data["customers"][target_cid]
                save_data(data)
                await update.message.reply_text("✅ حذف شد.", reply_markup=admin_keyboard())
            else:
                await update.message.reply_text("❌ پیدا نشد.", reply_markup=admin_keyboard())
            return

        if mode == "admin_set_user_name_id":
            if text in data["users"]:
                context.user_data["target_user_id"] = text
                context.user_data["mode"] = "admin_set_user_name_value"
                await update.message.reply_text("👤 نام و فامیل را بفرستید:", reply_markup=exit_keyboard())
            else:
                await update.message.reply_text("❌ این آیدی در لیست کاربران نیست.", reply_markup=admin_keyboard())
                clear_mode(context)
            return

        if mode == "admin_set_user_name_value":
            target = context.user_data.get("target_user_id")
            if target in data["users"]:
                data["users"][target]["name"] = text
                save_data(data)
                await update.message.reply_text("✅ نام ثبت شد.", reply_markup=admin_keyboard())
            clear_mode(context)
            return

        if mode == "admin_birthday_id":
            if text in data["users"]:
                context.user_data["target_user_id"] = text
                context.user_data["mode"] = "admin_birthday_value"
                await update.message.reply_text("🎂 تاریخ تولد جدید (فرمت 07-25):", reply_markup=exit_keyboard())
            else:
                await update.message.reply_text("❌ این آیدی پیدا نشد.", reply_markup=admin_keyboard())
                clear_mode(context)
            return

        if mode == "admin_birthday_value":
            target = context.user_data.get("target_user_id")
            clear_mode(context)
            if BIRTHDAY_RE.match(text) and target in data["users"]:
                data["users"][target]["birthday"] = text
                save_data(data)
                await update.message.reply_text("✅ تاریخ تولد ثبت شد.", reply_markup=admin_keyboard())
            else:
                await update.message.reply_text("❌ فرمت اشتباه بود.", reply_markup=admin_keyboard())
            return

        if mode == "admin_msg_user_id":
            context.user_data["target_user_id"] = text
            context.user_data["mode"] = "admin_msg_user_text"
            await update.message.reply_text("✏️ متن پیام را بنویسید:", reply_markup=exit_keyboard())
            return

        if mode == "admin_msg_user_text":
            target = context.user_data.get("target_user_id")
            clear_mode(context)
            try:
                await context.bot.send_message(int(target), f"📩 پیام از طرف فروشگاه:\n\n{text}")
                await update.message.reply_text("✅ ارسال شد.", reply_markup=admin_keyboard())
            except Exception:
                await update.message.reply_text("❌ ارسال نشد (آیدی نادرست؟)", reply_markup=admin_keyboard())
            return

        if mode == "admin_broadcast":
            clear_mode(context)
            count = 0
            for uid_str in data["users"]:
                try:
                    await context.bot.send_message(int(uid_str), f"📢 پیام از طرف فروشگاه:\n\n{text}")
                    count += 1
                except Exception:
                    continue
            await update.message.reply_text(f"✅ پیام به {count} کاربر ارسال شد.", reply_markup=admin_keyboard())
            return

    # ============ DEFAULT ============
    if is_admin(uid):
        await update.message.reply_text("از دکمه‌های پنل استفاده کنید 👇", reply_markup=admin_keyboard())
    else:
        await update.message.reply_text("از دکمه‌های منو استفاده کنید 👇", reply_markup=main_keyboard())


# ================= DAILY JOB: reminders & birthdays =================
async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%m-%d")
    for uid_str, u in data["users"].items():
        # birthday
        if u.get("birthday") == today:
            try:
                await context.bot.send_message(
                    int(uid_str),
                    "🎂 تولدتون مبارک! 🎉\nبه افتخار شما یک کد تخفیف ویژه فعال شد: BDAY10"
                )
            except Exception:
                pass
        # inactivity (7+ days)
        try:
            last = datetime.strptime(u.get("last_active", now_str()), "%Y-%m-%d %H:%M")
            if datetime.now() - last > timedelta(days=7):
                await context.bot.send_message(
                    int(uid_str),
                    "🥲 دلتنگتون بودیم! بیا ببین چه تخفیف‌های جدیدی منتظرته 🎁"
                )
        except Exception:
            pass


# ================= RUN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    if app.job_queue:
        app.job_queue.run_daily(daily_job, time=datetime.now().time())

    print("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
