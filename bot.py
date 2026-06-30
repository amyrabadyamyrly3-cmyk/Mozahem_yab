import os
import re
import json
import time
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
BIRTHDAY_RE = re.compile(r"^\d{2}-\d{2}$")
URL_RE = re.compile(r"https?://\S+")

SPAM_COOLDOWN = 1.2  # seconds


# ================= DATA =================
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d.setdefault("customers", {})
    d.setdefault("users", {})
    d.setdefault("relay", {})       # msg_id(str) -> {user_id, ticket_id}
    d.setdefault("tickets", {})     # ticket_id(str) -> {user_id, type, text, status, answer, created}
    d.setdefault("ticket_counter", 1000)
    d.setdefault("quick_replies", [])
    d.setdefault("settings", {})
    s = d["settings"]
    s.setdefault("vip_message", "💎 برای خرید حساب VIP و اطلاعات بیشتر، لطفاً منتظر بمانید، به‌زودی ادمین با شما در تماس خواهد بود.")
    s.setdefault("support_prompt", "🆘 پیام خود را برای پشتیبانی بنویسید:")
    s.setdefault("buy_prompt", "🛒 درخواست خرید خود را بنویسید:")
    s.setdefault("maintenance", False)
    s.setdefault("maintenance_message", "🌙 ربات موقتاً در دسترس نیست. لطفاً بعداً مراجعه کنید.")
    return d


def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


data = load_data()
spam_guard = {}


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def get_user(uid):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {
            "points": 0,
            "vip": False,
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


def new_ticket(uid, kind, text):
    data["ticket_counter"] += 1
    tid = str(data["ticket_counter"])
    data["tickets"][tid] = {
        "user_id": uid,
        "type": kind,
        "text": text,
        "status": "open",
        "answer": None,
        "created": now_str(),
    }
    save_data(data)
    return tid


# ================= KEYBOARDS =================
def main_keyboard():
    return ReplyKeyboardMarkup([
        ["🔍 جستجو با شماره", "👤 جستجو با نام"],
        ["🛒 ثبت درخواست خرید", "🆘 پشتیبانی"],
        ["💳 حساب من", "🎁 دعوت از دوستان"],
        ["💎 خرید VIP", "📦 بمبر"],
        ["📥 دانلود از شبکه‌های اجتماعی", "🔎 پیگیری درخواست"],
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
        ["✏️ ویرایش پیام‌ها", "💬 پاسخ‌های آماده"],
        ["📨 پیام‌های نخوانده", "🌙 فعال/غیرفعال ربات"],
        ["🔙 خروج به منو"],
    ], resize_keyboard=True)


def edit_prompt_keyboard():
    return ReplyKeyboardMarkup([
        ["💎 متن VIP", "🆘 متن پشتیبانی"],
        ["🛒 متن خرید"],
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
    msg = (
        f"🔔 جستجوی جدید\n\n"
        f"👤 کاربر: {name} (آیدی: {user.id})\n"
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
    clear_mode(context)

    if context.args:
        ref_code = context.args[0]
        if ref_code != str(uid) and u["referred_by"] is None and ref_code in data["users"]:
            u["referred_by"] = ref_code
            u["points"] += 20
            data["users"][ref_code]["points"] += 20
            save_data(data)
            try:
                await context.bot.send_message(int(ref_code), "🎁 یک دوست با کد دعوت شما عضو شد! ۲۰ امتیاز گرفتید.")
            except Exception:
                pass

    name = update.effective_user.first_name or ""
    await update.message.reply_text(
        f"👋 سلام {name} عزیز!\n\n🌟 به ربات شاپ ما خوش آمدید\n🔹 یک گزینه را انتخاب کنید:",
        reply_markup=main_keyboard()
    )


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    clear_mode(context)
    await update.message.reply_text("👑 پنل مدیریت فعال شد", reply_markup=admin_keyboard())


# ================= MAIN HANDLER =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    uid = update.effective_user.id
    user_obj = update.effective_user
    admin = is_admin(uid)

    # ---- anti-spam (non-admin only) ----
    if not admin:
        last = spam_guard.get(uid, 0)
        now_ts = time.time()
        if now_ts - last < SPAM_COOLDOWN:
            return
        spam_guard[uid] = now_ts

    touch_user(uid)

    # ---- Admin reply to relayed ticket message ----
    if admin and update.message.reply_to_message:
        rid = str(update.message.reply_to_message.message_id)
        if rid in data["relay"]:
            info = data["relay"][rid]
            target = info["user_id"]
            tid = info.get("ticket_id")
            reply_text = text
            if text.startswith("#"):
                try:
                    idx = int(text[1:]) - 1
                    reply_text = data["quick_replies"][idx]
                except Exception:
                    await update.message.reply_text("❌ شماره پاسخ آماده نامعتبر است.")
                    return
            try:
                prefix = f"💬 پاسخ ادمین"
                if tid:
                    prefix += f" (پیگیری #{tid})"
                await context.bot.send_message(target, f"{prefix}:\n\n{reply_text}")
                if tid and tid in data["tickets"]:
                    data["tickets"][tid]["status"] = "answered"
                    data["tickets"][tid]["answer"] = reply_text
                    save_data(data)
                await update.message.reply_text("✅ پیام ارسال شد.")
            except Exception:
                await update.message.reply_text("❌ ارسال نشد.")
            return

    mode = context.user_data.get("mode")

    # ---- universal exit ----
    if text == "🔙 خروج به منو":
        clear_mode(context)
        if admin:
            await update.message.reply_text("بازگشت به پنل مدیریت", reply_markup=admin_keyboard())
        else:
            await update.message.reply_text("بازگشت به منوی اصلی", reply_markup=main_keyboard())
        return

    # ---- maintenance mode block (customers only) ----
    if not admin and data["settings"]["maintenance"] and text != "/start":
        await update.message.reply_text(data["settings"]["maintenance_message"])
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
        await update.message.reply_text(data["settings"]["buy_prompt"], reply_markup=exit_keyboard())
        return

    if text == "🆘 پشتیبانی":
        context.user_data["mode"] = "support"
        await update.message.reply_text(data["settings"]["support_prompt"], reply_markup=exit_keyboard())
        return

    if text == "💳 حساب من":
        u = get_user(uid)
        bday = u["birthday"] or "ثبت نشده"
        vip_line = "بله ✅" if u["vip"] else "خیر"
        await update.message.reply_text(
            f"💳 حساب کاربری شما\n\n"
            f"🆔 آیدی: {uid}\n"
            f"⭐ امتیاز: {u['points']}\n"
            f"👑 وضعیت VIP: {vip_line}\n"
            f"🎂 تاریخ تولد: {bday}\n\n"
            f"برای ثبت/تغییر تاریخ تولد (فرمت ماه-روز مثل 07-25) همینجا بفرستید:"
        )
        context.user_data["mode"] = "set_birthday"
        return

    if text == "🎁 دعوت از دوستان":
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={uid}"
        await update.message.reply_text(
            f"🎁 دوستان خود را دعوت کنید!\n\n🔗 لینک دعوت شما:\n{link}\n\n"
            "✨ با هر دعوت موفق، شما و دوستتان هر دو ۲۰ امتیاز می‌گیرید."
        )
        return

    if text == "💎 خرید VIP":
        await update.message.reply_text(data["settings"]["vip_message"])
        await notify_admin(context, f"💎 درخواست VIP\n👤 {user_obj.first_name} (آیدی: {uid})")
        return

    if text == "📦 بمبر":
        context.user_data["mode"] = "bomber_phone"
        await update.message.reply_text(
            "📦 شماره تلفن خود را وارد کنید\n\nفرمت صحیح: 09127654123",
            reply_markup=exit_keyboard()
        )
        return

    if text == "📥 دانلود از شبکه‌های اجتماعی":
        context.user_data["mode"] = "social_dl"
        await update.message.reply_text(
            "📥 لینک پست/ویدیو (اینستاگرام، یوتیوب و...) را بفرستید:",
            reply_markup=exit_keyboard()
        )
        return

    if text == "🔎 پیگیری درخواست":
        context.user_data["mode"] = "track_ticket"
        await update.message.reply_text("🔎 شماره پیگیری خود را وارد کنید (مثل 1024):", reply_markup=exit_keyboard())
        return

    # ============ ADMIN MENU BUTTONS ============
    if admin:
        if text == "➕ افزودن مشتری تکی":
            context.user_data["mode"] = "admin_add_name"
            await update.message.reply_text("👤 نام و فامیل مشتری جدید را بنویسید:", reply_markup=exit_keyboard())
            return

        if text == "📋 افزودن مشتری گروهی":
            context.user_data["mode"] = "admin_add_bulk"
            await update.message.reply_text(
                "📋 هر خط: نام|شماره\n\nمثال:\nعلی رضایی|09120000000",
                reply_markup=exit_keyboard()
            )
            return

        if text == "✏️ ویرایش مشتری":
            context.user_data["mode"] = "admin_edit_find"
            await update.message.reply_text("📞 شماره مشتری برای ویرایش را بفرستید:", reply_markup=exit_keyboard())
            return

        if text == "🗑 حذف مشتری":
            context.user_data["mode"] = "admin_delete"
            await update.message.reply_text("📞 شماره مشتری برای حذف را بفرستید:", reply_markup=exit_keyboard())
            return

        if text == "📊 آمار فروش":
            await update.message.reply_text(
                f"📊 آمار فروش\n\n👥 تعداد کل مشتریان: {len(data['customers'])}\n"
                f"👤 تعداد کاربران ربات: {len(data['users'])}\n"
                f"📨 تیکت‌های باز: {sum(1 for t in data['tickets'].values() if t['status']=='open')}"
            )
            return

        if text == "📤 خروجی لیست":
            customers = data["customers"]
            if not customers:
                await update.message.reply_text("📭 لیست خالی است.")
                return
            content = "\n".join(f"{c['name']} - {c['phone']}" for c in customers.values())
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

        if text == "✏️ ویرایش پیام‌ها":
            await update.message.reply_text("کدام پیام را می‌خواهید ویرایش کنید؟", reply_markup=edit_prompt_keyboard())
            return

        if text == "💎 متن VIP":
            context.user_data["mode"] = "admin_edit_vip_text"
            await update.message.reply_text(
                f"متن فعلی:\n\n{data['settings']['vip_message']}\n\nمتن جدید را بفرستید:",
                reply_markup=exit_keyboard()
            )
            return

        if text == "🆘 متن پشتیبانی":
            context.user_data["mode"] = "admin_edit_support_text"
            await update.message.reply_text(
                f"متن فعلی:\n\n{data['settings']['support_prompt']}\n\nمتن جدید را بفرستید:",
                reply_markup=exit_keyboard()
            )
            return

        if text == "🛒 متن خرید":
            context.user_data["mode"] = "admin_edit_buy_text"
            await update.message.reply_text(
                f"متن فعلی:\n\n{data['settings']['buy_prompt']}\n\nمتن جدید را بفرستید:",
                reply_markup=exit_keyboard()
            )
            return

        if text == "💬 پاسخ‌های آماده":
            qrs = data["quick_replies"]
            msg = "💬 پاسخ‌های آماده:\n\n"
            if qrs:
                for i, q in enumerate(qrs, 1):
                    msg += f"{i}. {q}\n"
            else:
                msg += "هیچ پاسخی ثبت نشده.\n"
            msg += (
                "\n➕ برای افزودن: متن را با پیشوند + بفرستید (مثال: +موجود نیست)\n"
                "🗑 برای حذف: شماره را با پیشوند - بفرستید (مثال: -2)\n"
                "ℹ️ برای استفاده هنگام پاسخ به مشتری، کافیست #شماره را Reply کنید (مثال: #1)"
            )
            context.user_data["mode"] = "admin_quick_manage"
            await update.message.reply_text(msg[:4000], reply_markup=exit_keyboard())
            return

        if text == "📨 پیام‌های نخوانده":
            open_tickets = {tid: t for tid, t in data["tickets"].items() if t["status"] == "open"}
            if not open_tickets:
                await update.message.reply_text("✅ همه پیام‌ها پاسخ داده شده‌اند.")
                return
            msg = "📨 پیام‌های نخوانده:\n\n"
            for tid, t in open_tickets.items():
                msg += f"#{tid} | {t['type']} | {t['text'][:40]}\n"
            await update.message.reply_text(msg[:4000])
            return

        if text == "🌙 فعال/غیرفعال ربات":
            data["settings"]["maintenance"] = not data["settings"]["maintenance"]
            save_data(data)
            state = "غیرفعال 🌙" if data["settings"]["maintenance"] else "فعال ✅"
            await update.message.reply_text(f"وضعیت ربات: {state}", reply_markup=admin_keyboard())
            return

    # ============ MODE PROCESSING (CUSTOMER) ============
    if mode == "search_phone":
        clear_mode(context)
        found_c = next((c for c in data["customers"].values() if c["phone"] == text), None)
        await notify_admin_search(context, user_obj, "شماره", text, bool(found_c))
        if found_c:
            await update.message.reply_text(f"✅ {found_c['name']} - {found_c['phone']}", reply_markup=main_keyboard())
        else:
            await update.message.reply_text("❌ مشتری‌ای با این شماره پیدا نشد.", reply_markup=main_keyboard())
        return

    if mode == "search_name":
        clear_mode(context)
        found_c = next((c for c in data["customers"].values() if c["name"] == text), None)
        await notify_admin_search(context, user_obj, "نام", text, bool(found_c))
        if found_c:
            await update.message.reply_text(f"✅ {found_c['name']} - {found_c['phone']}", reply_markup=main_keyboard())
        else:
            await update.message.reply_text("❌ مشتری‌ای با این نام پیدا نشد.", reply_markup=main_keyboard())
        return

    if mode == "buy_request":
        clear_mode(context)
        tid = new_ticket(uid, "خرید", text)
        sent = await context.bot.send_message(
            ADMIN_ID, f"🛒 درخواست خرید جدید (پیگیری #{tid})\n👤 {user_obj.first_name} (آیدی: {uid})\n\n📝 {text}"
        )
        data["relay"][str(sent.message_id)] = {"user_id": uid, "ticket_id": tid}
        save_data(data)
        await update.message.reply_text(f"✅ درخواست شما ثبت شد.\n🔎 شماره پیگیری: {tid}", reply_markup=main_keyboard())
        return

    if mode == "support":
        clear_mode(context)
        tid = new_ticket(uid, "پشتیبانی", text)
        sent = await context.bot.send_message(
            ADMIN_ID, f"🆘 پیام پشتیبانی (پیگیری #{tid})\n👤 {user_obj.first_name} (آیدی: {uid})\n\n📝 {text}"
        )
        data["relay"][str(sent.message_id)] = {"user_id": uid, "ticket_id": tid}
        save_data(data)
        await update.message.reply_text(f"✅ پیام شما ثبت شد.\n🔎 شماره پیگیری: {tid}", reply_markup=main_keyboard())
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
            await update.message.reply_text("❌ شماره وارد شده اشتباه است.\nفرمت صحیح: 09127654123", reply_markup=exit_keyboard())
        return

    if mode == "track_ticket":
        clear_mode(context)
        t = data["tickets"].get(text)
        if not t or t["user_id"] != uid:
            await update.message.reply_text("❌ تیکتی با این شماره برای شما پیدا نشد.", reply_markup=main_keyboard())
        elif t["status"] == "answered":
            await update.message.reply_text(f"✅ پاسخ داده شده:\n\n{t['answer']}", reply_markup=main_keyboard())
        else:
            await update.message.reply_text("⏳ هنوز پاسخ داده نشده. لطفاً صبر کنید.", reply_markup=main_keyboard())
        return

    if mode == "social_dl":
        clear_mode(context)
        if not URL_RE.search(text):
            await update.message.reply_text("❌ لینک معتبر نیست.", reply_markup=main_keyboard())
            return
        await update.message.reply_text("⏳ در حال دانلود... کمی صبر کنید.")
        try:
            import yt_dlp
            url = URL_RE.search(text).group(0)
            outtmpl = f"dl_{uid}_{int(time.time())}.%(ext)s"
            ydl_opts = {
                "outtmpl": outtmpl,
                "format": "best[filesize<50M]/best",
                "quiet": True,
                "noplaylist": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            await update.message.reply_document(document=open(filename, "rb"))
            try:
                os.remove(filename)
            except Exception:
                pass
        except Exception:
            await update.message.reply_text("❌ دانلود ناموفق بود. لینک را بررسی کنید یا بعداً تلاش کنید.")
        await update.message.reply_text("منوی اصلی:", reply_markup=main_keyboard())
        return

    # ============ ADMIN MODE PROCESSING ============
    if admin:
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
            target_cid = next((cid for cid, c in data["customers"].items() if c["phone"] == text), None)
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
            target_cid = next((cid for cid, c in data["customers"].items() if c["phone"] == text), None)
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
                await update.message.reply_text("❌ این آیدی پیدا نشد.", reply_markup=admin_keyboard())
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

        if mode == "admin_edit_vip_text":
            clear_mode(context)
            data["settings"]["vip_message"] = text
            save_data(data)
            await update.message.reply_text("✅ متن VIP بروزرسانی شد.", reply_markup=admin_keyboard())
            return

        if mode == "admin_edit_support_text":
            clear_mode(context)
            data["settings"]["support_prompt"] = text
            save_data(data)
            await update.message.reply_text("✅ متن پشتیبانی بروزرسانی شد.", reply_markup=admin_keyboard())
            return

        if mode == "admin_edit_buy_text":
            clear_mode(context)
            data["settings"]["buy_prompt"] = text
            save_data(data)
            await update.message.reply_text("✅ متن خرید بروزرسانی شد.", reply_markup=admin_keyboard())
            return

        if mode == "admin_quick_manage":
            if text.startswith("+"):
                data["quick_replies"].append(text[1:].strip())
                save_data(data)
                await update.message.reply_text("✅ افزوده شد.", reply_markup=exit_keyboard())
            elif text.startswith("-"):
                try:
                    idx = int(text[1:].strip()) - 1
                    removed = data["quick_replies"].pop(idx)
                    save_data(data)
                    await update.message.reply_text(f"✅ حذف شد: {removed}", reply_markup=exit_keyboard())
                except Exception:
                    await update.message.reply_text("❌ شماره نامعتبر.", reply_markup=exit_keyboard())
            else:
                await update.message.reply_text("از + برای افزودن و - برای حذف استفاده کنید.", reply_markup=exit_keyboard())
            return

    # ============ DEFAULT ============
    if admin:
        await update.message.reply_text("از دکمه‌های پنل استفاده کنید 👇", reply_markup=admin_keyboard())
    else:
        await update.message.reply_text("از دکمه‌های منو استفاده کنید 👇", reply_markup=main_keyboard())


# ================= DAILY JOB =================
async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%m-%d")
    for uid_str, u in data["users"].items():
        if u.get("birthday") == today:
            try:
                await context.bot.send_message(int(uid_str), "🎂 تولدتون مبارک! 🎉\nکد تخفیف ویژه: BDAY10")
            except Exception:
                pass
        try:
            last = datetime.strptime(u.get("last_active", now_str()), "%Y-%m-%d %H:%M")
            if datetime.now() - last > timedelta(days=7):
                await context.bot.send_message(int(uid_str), "🥲 دلتنگتون بودیم! بیا ببین چه تخفیف‌های جدیدی منتظرته 🎁")
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
