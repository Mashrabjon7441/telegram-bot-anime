import os

# Telegram Bot Token (Get it from @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8920248396:AAFPBMGG3XL12NFCK_6QLk7-bVm4HIpgPJ8")

# Downloader Bot Token (Get it from @BotFather)
DOWNLOADER_BOT_TOKEN = os.getenv("DOWNLOADER_BOT_TOKEN", "6317346772:AAHk97Ik2RS-0WsOZ5qP_OJORRjd1MzFhhk")

# Administrator Telegram IDs (List of integers). Only these users can add/delete movies.
# You can get your ID from bots like @userinfobot or @dtgbot
ADMIN_IDS = [5899807377] # Replace with your actual user ID(s)

# Doimiy homiy kanallar ro'yxati (Agar bot ichidan kiritilmasa, shulardan foydalanadi).
# Format: [{"channel_id": "@kanal_username_yoki_id", "title": "Kanal nomi", "invite_link": "https://t.me/link"}]
MANDATORY_CHANNELS = [
    # {
    #     "channel_id": "@my_channel_username", 
    #     "title": "Kanalimizga A'zo bo'ling", 
    #     "invite_link": "https://t.me/my_channel_username"
    # }
]
