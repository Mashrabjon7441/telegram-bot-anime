import os

# Telegram Bot Token (Get it from @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8920248396:AAFPBMGG3XL12NFCK_6QLk7-bVm4HIpgPJ8")

# Downloader Bot Token (Get it from @BotFather)
DOWNLOADER_BOT_TOKEN = os.getenv("DOWNLOADER_BOT_TOKEN", "8044738592:AAH9v76Qn-78_pQnZDw7QJkwG899_example")

# Administrator Telegram IDs (List of integers). Only these users can add/delete movies.
# You can get your ID from bots like @userinfobot or @dtgbot
ADMIN_IDS = [5899807377] # Replace with your actual user ID(s)
