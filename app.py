import os
import threading
from flask import Flask, jsonify
from main import bot
import database

app = Flask(__name__)

@app.route('/')
def home():
    try:
        users = database.get_users_count()
        movies = len(database.get_all_movies())
        bot_info = bot.get_me()
        return jsonify({
            "status": "online",
            "bot_name": bot_info.first_name,
            "bot_username": f"@{bot_info.username}",
            "total_users": users,
            "total_movies": movies
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

if __name__ == '__main__':
    # Initialize DB (if not already done)
    database.init_db()
    
    # Start bot polling in a background thread to keep it alive
    print("Starting bot polling in background thread...")
    bot_thread = threading.Thread(target=bot.infinity_polling, daemon=True)
    bot_thread.start()
    
    # Run the web server to satisfy Render's port binding health-checks
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting web server on port {port}...")
    app.run(host="0.0.0.0", port=port)
