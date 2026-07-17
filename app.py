import os
import threading
from flask import Flask, jsonify
from main import bot
import database

try:
    from downloader_bot import bot as downloader_bot_instance
except Exception as e:
    print("Failed to import downloader_bot:", e)
    downloader_bot_instance = None

app = Flask(__name__)

@app.route('/')
def home():
    try:
        users = database.get_users_count()
        movies = len(database.get_all_movies())
        bot_info = bot.get_me()
        
        info_dict = {
            "status": "online",
            "kino_bot_name": bot_info.first_name,
            "kino_bot_username": f"@{bot_info.username}",
            "total_users": users,
            "total_movies": movies
        }
        
        if downloader_bot_instance:
            try:
                dl_info = downloader_bot_instance.get_me()
                info_dict["downloader_bot_name"] = dl_info.first_name
                info_dict["downloader_bot_username"] = f"@{dl_info.username}"
            except Exception:
                info_dict["downloader_bot"] = "Token not configured or invalid"
                
        return jsonify(info_dict)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

def run_downloader():
    if not downloader_bot_instance:
        return
    print("Starting downloader bot polling...")
    try:
        downloader_bot_instance.infinity_polling()
    except Exception as e:
        print("Downloader Bot polling thread failed:", e)

if __name__ == '__main__':
    # Initialize DB (if not already done)
    database.init_db()
    
    # Start bot polling in a background thread to keep it alive
    print("Starting kino bot polling in background thread...")
    bot_thread = threading.Thread(target=bot.infinity_polling, daemon=True)
    bot_thread.start()
    
    # Start downloader bot in background thread
    dl_thread = threading.Thread(target=run_downloader, daemon=True)
    dl_thread.start()
    
    # Run the web server to satisfy Render's port binding health-checks
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting web server on port {port}...")
    app.run(host="0.0.0.0", port=port)

