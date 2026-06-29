import sqlite3

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

# 👤 کاربران
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    points INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    searches INTEGER DEFAULT 0,
    vip INTEGER DEFAULT 0
)
""")

# 🔍 لاگ‌ها
cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    query TEXT,
    time TEXT
)
""")

conn.commit()
