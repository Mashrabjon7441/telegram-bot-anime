import os
import time
import threading
import urllib.request
from flask import Flask, jsonify, request, render_template

import database
import config

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

# ── Botlarni fon oqimida to'xtovsiz ishlatuvchi funksiya ────────
def run_bot_forever(bot_instance, name):
    """Bot har qanday sababdan to'xtasa avtomatik qayta ishga tushiradi."""
    if not bot_instance:
        print(f"[{name}] Bot topilmadi, ishga tushirilmadi.")
        return
    while True:
        try:
            print(f"[{name}] Polling boshlandi...")
            bot_instance.infinity_polling(
                timeout=60,
                long_polling_timeout=55,
                none_stop=True,
                skip_pending=True,
                allowed_updates=["message", "callback_query", "my_chat_member"]
            )
        except Exception as e:
            wait = 15
            print(f"[{name}] Polling xatosi: {e}")
            print(f"[{name}] {wait} soniyadan keyin qayta uriniladi...")
            time.sleep(wait)

# ── Botlarni alohida threadlarda ishga tushirish ───────────────
kino_thread = threading.Thread(
    target=run_bot_forever,
    args=(kino_bot, "Kino Bot"),
    daemon=True
)
kino_thread.start()

time.sleep(3)  # Botlar ulanish to'qnashuvini oldini olish uchun

dl_thread = threading.Thread(
    target=run_bot_forever,
    args=(dl_bot, "Downloader Bot"),
    daemon=True
)
dl_thread.start()

# ── Flask veb-server ──────────────────────────────────────────────
app = Flask(__name__, template_folder='templates')

def is_admin_auth():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        auth_header = request.args.get('key')
    return auth_header == config.ADMIN_PASSWORD

@app.route('/')
def home():
    # render_template default templates/index.html ni yuklaydi
    return render_template('index.html')

@app.route('/health')
def health():
    return "OK", 200

# ── API Endpoints ──────────────────────────────────────────────────

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    password = data.get('password')
    if password == config.ADMIN_PASSWORD:
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Noto'g'ri parol!"}), 401

@app.route('/api/stats', methods=['GET'])
def api_stats():
    if not is_admin_auth():
        return jsonify({"message": "Ruxsat yo'q!"}), 401

    # Kino bot status check
    kino_online = False
    kino_username = ""
    if kino_bot:
        try:
            info = kino_bot.get_me()
            kino_online = True
            kino_username = info.username
        except Exception:
            pass

    # Downloader bot status check
    dl_online = False
    dl_username = ""
    if dl_bot:
        try:
            info = dl_bot.get_me()
            dl_online = True
            dl_username = info.username
        except Exception:
            pass

    # Channels list formatting
    raw_channels = database.get_admin_channels()
    channels_list = []
    for ch_id, title, username, invite, is_mandatory in raw_channels:
        channels_list.append({
            "channel_id": ch_id,
            "title": title,
            "username": username,
            "invite_link": invite,
            "is_mandatory": bool(is_mandatory)
        })

    # Movies with episodes mapping
    raw_movies = database.get_all_movies()
    movies_list = []
    for code, title in raw_movies:
        movie_data = database.get_movie(code)
        caption = movie_data[2] if movie_data else ""
        episodes_raw = database.get_episodes(code)
        episodes = [{"id": ep[0], "title": ep[1], "file_id": ep[2]} for ep in episodes_raw]
        movies_list.append({
            "code": code,
            "title": title,
            "caption": caption,
            "episodes": episodes
        })

    return jsonify({
        "kino_users": database.get_users_count(),
        "downloader_users": database.get_downloader_users_count(),
        "total_movies": len(raw_movies),
        "kino_bot_online": kino_online,
        "kino_username": kino_username,
        "dl_bot_online": dl_online,
        "dl_username": dl_username,
        "channels": channels_list,
        "movies_list": movies_list
    })

@app.route('/api/movies/add', methods=['POST'])
def api_movies_add():
    if not is_admin_auth():
        return jsonify({"message": "Ruxsat yo'q!"}), 401
    data = request.get_json() or {}
    code = data.get('code')
    title = data.get('title')
    caption = data.get('caption', '')
    if not code or not title:
        return jsonify({"success": False, "message": "Kod va Sarlavha talab qilinadi!"}), 400

    success = database.add_movie(code, title, caption)
    return jsonify({"success": success})

@app.route('/api/movies/delete', methods=['POST'])
def api_movies_delete():
    if not is_admin_auth():
        return jsonify({"message": "Ruxsat yo'q!"}), 401
    data = request.get_json() or {}
    code = data.get('code')
    if not code:
        return jsonify({"success": False, "message": "Kod talab qilinadi!"}), 400

    success = database.delete_movie(code)
    return jsonify({"success": success})

@app.route('/api/episodes/add', methods=['POST'])
def api_episodes_add():
    if not is_admin_auth():
        return jsonify({"message": "Ruxsat yo'q!"}), 401
    data = request.get_json() or {}
    movie_code = data.get('movie_code')
    episode_title = data.get('episode_title')
    file_id = data.get('file_id')
    if not movie_code or not episode_title or not file_id:
        return jsonify({"success": False, "message": "Barcha maydonlar to'ldirilishi shart!"}), 400

    success = database.add_episode(movie_code, episode_title, file_id)
    return jsonify({"success": success})

@app.route('/api/episodes/delete', methods=['POST'])
def api_episodes_delete():
    if not is_admin_auth():
        return jsonify({"message": "Ruxsat yo'q!"}), 401
    data = request.get_json() or {}
    ep_id = data.get('id')
    if not ep_id:
        return jsonify({"success": False, "message": "ID talab qilinadi"}), 400

    success = database.delete_episode(ep_id)
    return jsonify({"success": success})

@app.route('/api/channels/add', methods=['POST'])
def api_channels_add():
    if not is_admin_auth():
        return jsonify({"message": "Ruxsat yo'q!"}), 401
    data = request.get_json() or {}
    channel_id = data.get('channel_id')
    title = data.get('title')
    invite_link = data.get('invite_link')
    if not channel_id or not title or not invite_link:
        return jsonify({"success": False, "message": "Barcha ma'lumotlar talab etiladi!"}), 400

    database.save_admin_channel(channel_id, title, None, invite_link)
    database.set_channel_mandatory(channel_id, 1) # Default active
    return jsonify({"success": True})

@app.route('/api/channels/delete', methods=['POST'])
def api_channels_delete():
    if not is_admin_auth():
        return jsonify({"message": "Ruxsat yo'q!"}), 401
    data = request.get_json() or {}
    channel_id = data.get('channel_id')
    if not channel_id:
        return jsonify({"success": False, "message": "Kanal ID kiritilishi shart!"}), 400

    database.remove_admin_channel(channel_id)
    return jsonify({"success": True})

@app.route('/api/channels/toggle_mandatory', methods=['POST'])
def api_channels_toggle():
    if not is_admin_auth():
        return jsonify({"message": "Ruxsat yo'q!"}), 401
    data = request.get_json() or {}
    channel_id = data.get('channel_id')
    is_mandatory = data.get('is_mandatory')
    if not channel_id or is_mandatory is None:
        return jsonify({"success": False, "message": "Kanal yoki holat kiritilmagan!"}), 400

    database.set_channel_mandatory(channel_id, int(is_mandatory))
    return jsonify({"success": True})

@app.route('/api/broadcast', methods=['POST'])
def api_broadcast():
    if not is_admin_auth():
        return jsonify({"message": "Ruxsat yo'q!"}), 401
    data = request.get_json() or {}
    target = data.get('target', 'both')
    text = data.get('text', '')

    if not text:
        return jsonify({"success": False, "message": "Matn kiritilmadi!"}), 400

    kino_users = []
    dl_users = []
    if target in ['both', 'kino']:
        kino_users = database.get_users()
    if target in ['both', 'downloader']:
        dl_users = database.get_downloader_users()

    # Unique list (agar foydalanuvchi ikkalasida ham bo'lsa)
    all_target_users = list(set(kino_users + dl_users))
    
    success_count = 0
    fail_count = 0

    # Broadcast thread or simple iterate
    for u_id in all_target_users:
        sent = False
        # Birinchi kino botdan yuborib ko'ramiz
        if kino_bot and u_id in kino_users:
            try:
                kino_bot.send_message(u_id, text, parse_mode="HTML")
                success_count += 1
                sent = True
            except Exception:
                pass

        # Agar birinchi bot yubora olmagan bo'lsa va downloader bot a'zosi bo'lsa
        if not sent and dl_bot and u_id in dl_users:
            try:
                dl_bot.send_message(u_id, text, parse_mode="HTML")
                success_count += 1
                sent = True
            except Exception:
                pass

        if not sent:
            fail_count += 1

    return jsonify({
        "success": True,
        "success_count": success_count,
        "fail_count": fail_count
    })

# ── Keep-Alive ping mexanizmi ─────────────────────────────────────
def keep_alive_ping():
    """
    Render'ni doimiy uyg'oq saqlash uchun /health ga ping yuborib turadi.
    Tashqari URL bo'lsa shuni oladi.
    """
    time.sleep(120)  # Bot start up kutish
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    port = int(os.environ.get("PORT", 5000))
    ping_url = f"{render_url}/health" if render_url else f"http://localhost:{port}/health"

    print(f"[Keep-Alive] Ping ishga tushdi: {ping_url}")
    while True:
        try:
            req = urllib.request.Request(ping_url, headers={"User-Agent": "UptimeKeepAlive/1.0"})
            urllib.request.urlopen(req, timeout=15)
            print("[Keep-Alive] ✅ Ping yuborildi!")
        except Exception as e:
            print(f"[Keep-Alive] ⚠️ Ping xatosi: {e}")
        time.sleep(10 * 60) # Har 10 daqiqa

ping_thread = threading.Thread(target=keep_alive_ping, daemon=True)
ping_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Web server starting on port {port}...")
    app.run(host="0.0.0.0", port=port)
