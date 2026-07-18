import os

# Telegram Bot Token (Get it from @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8920248396:AAFPBMGG3XL12NFCK_6QLk7-bVm4HIpgPJ8")

# Downloader Bot Token (Get it from @BotFather)
DOWNLOADER_BOT_TOKEN = os.getenv("DOWNLOADER_BOT_TOKEN", "6317346772:AAHk97Ik2RS-0WsOZ5qP_OJORRjd1MzFhhk")

# Administrator Telegram IDs (List of integers). Only these users can add/delete movies.
# You can get your ID from bots like @userinfobot or @dtgbot
ADMIN_IDS = [5899807377] # Replace with your actual user ID(s)

# ═══════════════════════════════════════════════════════════════
# MAJBURIY OBUNA KANALLAR ROYHATI
# Bu yerga yozing — Render restart bo'lsayam o'chmaydi!
#
# channel_id: @username yoki -100XXXXXXXXXX (raqamli ID)
# title: Tugmada ko'rinadigan kanal nomi
# invite_link: Kanalga havola (ochiq kanal: https://t.me/username)
#
# MISOL:
# MANDATORY_CHANNELS = [
#     {
#         "channel_id": "@mening_kanalim",
#         "title": "Kino kanalimiz",
#         "invite_link": "https://t.me/mening_kanalim"
#     },
#     {
#         "channel_id": "-1001234567890",
#         "title": "Ikkinchi kanal",
#         "invite_link": "https://t.me/+abcXYZ123"
#     }
# ]
# ═══════════════════════════════════════════════════════════════
MANDATORY_CHANNELS = [
    # Kanalingizni shu yerga qo'shing:
    # {
    #     "channel_id": "@kanal_username",
    #     "title": "Kanalimizga a'zo bo'ling",
    #     "invite_link": "https://t.me/kanal_username"
    # }
]
