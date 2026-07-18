import os
import time
import threading
import urllib.request
from flask import Flask, jsonify

import database

# ── Botlarni import qilish ──────────────────────────────────────
try:
    from main import bot as kino_bot
except Exception as e:
    print("CRITICAL: Failed to import kino bot:", e)
    kino_bot = None

try:
    from downloader_bot import bot as dl_bot
except Exception as e:
    print("CRITICAL: Failed to import downloader bot:", e)
    dl_bot = None

# ── Ma'lumotlar bazasini ishga tushirish ────────────────────────
database.init_db()

# ── Botlarni fon oqimida to'xtovsiz ishlatuvchi funksiyalar ─────
def run_bot_forever(bot_instance, name):
    """Bot to'xtaganda avtomatik qayta ishga tushiradi."""
    if not bot_instance:
        print(f"[{name}] Bot topilmadi, o'tkazib yuborildi.")
        return
    while True:
        try:
            print(f"[{name}] Polling boshlandi...")
            # none_stop=True: Har qanday xatoda polling o'chmaydi
            bot_instance.infinity_polling(
                timeout=30,
                long_polling_timeout=25,
                none_stop=True,
                restart_on_change=False,
                skip_pending=True
            )
        except Exception as e:
            print(f"[{name}] Polling xatosi: {e}. 10 soniyadan keyin qayta uriniladi...")
            time.sleep(10)

# ── Kino bot threadini ishga tushirish ──────────────────────────
kino_thread = threading.Thread(
    target=run_bot_forever,
    args=(kino_bot, "Kino Bot"),
    daemon=True
)
kino_thread.start()

# ── Downloader bot threadini ishga tushirish ────────────────────
dl_thread = threading.Thread(
    target=run_bot_forever,
    args=(dl_bot, "Downloader Bot"),
    daemon=True
)
dl_thread.start()

# ── Flask veb-server ─────────────────────────────────────────────
app = Flask(__name__)

@app.route('/')
def home():
    try:
        result = {
            "status": "online",
            "total_users": database.get_users_count(),
            "total_movies": len(database.get_all_movies()),
        }
        if kino_bot:
            try:
                info = kino_bot.get_me()
                result["kino_bot"] = f"@{info.username} ({info.first_name})"
            except Exception:
                result["kino_bot"] = "token error"
        if dl_bot:
            try:
                info = dl_bot.get_me()
                result["downloader_bot"] = f"@{info.username} ({info.first_name})"
            except Exception:
                result["downloader_bot"] = "token error"
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/health')
def health():
    return jsonify({"status": "alive", "time": time.time()})

# ── Keep-Alive: Render uxlatmasligi uchun ───────────────────────
def keep_alive_ping():
    """Har 10 daqiqada serverga ping yuborib, Render'ni uyquga ketishidan saqlaydi."""
    time.sleep(90)  # Botlar to'liq ishga tushguncha kut
    port = int(os.environ.get("PORT", 5000))
    url = f"http://localhost:{port}/health"
    while True:
        try:
            urllib.request.urlopen(url, timeout=10)
            print("[Keep-Alive] ✅ Ping muvaffaqiyatli!")
        except Exception as e:
            print(f"[Keep-Alive] ⚠️ Ping xatosi: {e}")
        time.sleep(10 * 60)

ping_thread = threading.Thread(target=keep_alive_ping, daemon=True)
ping_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Web server starting on port {port}...")
    app.run(host="0.0.0.0", port=port)
