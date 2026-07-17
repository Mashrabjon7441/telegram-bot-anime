import telebot
import os
import yt_dlp
import threading
import uuid
import config

bot = telebot.TeleBot(config.DOWNLOADER_BOT_TOKEN)

def is_valid_link(text):
    text = text.lower().strip()
    return any(domain in text for domain in [
        'youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com', 
        'facebook.com', 'fb.watch', 'twitter.com', 'x.com', 'pinterest.com'
    ])

@bot.message_handler(commands=['start'])
def start_cmd(message):
    welcome_text = (
        f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
        "🤖 Ijtimoiy tarmoqlardan video yuklovchi botga xush kelibsiz!\n"
        "Menga videoning havolasini yuboring, men uni sizga yuklab beraman.\n\n"
        "Qo'llab-quvvatlanadigan tarmoqlar:\n"
        "• YouTube (Shorts & Videos)\n"
        "• Instagram (Reels & Posts)\n"
        "• TikTok\n"
        "• Facebook\n"
        "• Pinterest, Twitter/X"
    )
    bot.send_message(message.chat.id, welcome_text)

@bot.message_handler(func=lambda msg: True)
def link_handler(message):
    text = message.text.strip()
    
    if not is_valid_link(text):
        bot.send_message(message.chat.id, "❌ Iltimos, faqat qo'llab-quvvatlanadigan ijtimoiy tarmoq havolasini (linkini) yuboring!")
        return

    # Process in a background thread to prevent Telegram timeout errors
    t = threading.Thread(target=download_and_send_video, args=(message, text))
    t.start()

def download_and_send_video(message, url):
    status_msg = bot.send_message(message.chat.id, "⏳ Havola tekshirilmoqda va video yuklab olinmoqda... Iltimos kuting...")
    
    # We generate a unique temporary filename
    temp_id = str(uuid.uuid4())
    out_tmpl = f"temp_download_{temp_id}.%(ext)s"
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # download mp4 format
        'outtmpl': out_tmpl,
        'max_filesize': 50 * 1024 * 1024, # limit download to 50MB
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info & download
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # If for some reason the filename has a different extension than downloaded
            ext = info.get('ext', 'mp4')
            downloaded_file = filename
            if not os.path.exists(downloaded_file):
                # Search for any file with temp_download_{temp_id}
                for f in os.listdir('.'):
                    if f.startswith(f"temp_download_{temp_id}"):
                        downloaded_file = f
                        break
            
            if os.path.exists(downloaded_file):
                bot.edit_message_text("📤 Video yuklab olindi! Telegramga yuborilmoqda...", message.chat.id, status_msg.message_id)
                bot.send_chat_action(message.chat.id, 'upload_video')
                
                title = info.get('title', 'Video')
                caption = f"🎬 **Video nomi:** {title}\n🤖 **Bot:** @{bot.get_me().username}"
                
                with open(downloaded_file, 'rb') as f:
                    try:
                        bot.send_video(message.chat.id, f, caption=caption, parse_mode="Markdown")
                    except Exception:
                        f.seek(0)
                        bot.send_document(message.chat.id, f, caption=caption, parse_mode="Markdown")
                        
                try:
                    bot.delete_message(message.chat.id, status_msg.message_id)
                except Exception:
                    pass
            else:
                bot.edit_message_text("❌ Videoni yuklab olishda xatolik yuz berdi yoki video o'lchami ruxsat etilgan limitdan (50MB) katta.", message.chat.id, status_msg.message_id)
                
    except Exception as e:
        error_msg = str(e)
        if "max-filesize" in error_msg.lower() or "larger than max-filesize" in error_msg.lower():
             bot.edit_message_text("⚠️ **Xatolik:** Ushbu video hajmi o'ta katta (50MB limitidan yuqori). Telegram orqali yuborib bo'lmaydi.", message.chat.id, status_msg.message_id)
        else:
             bot.edit_message_text(f"❌ Yuklab olishda xatolik yuz berdi. Havola to'g'ri ekanligini yoki video ommaga ochiqligini tekshiring.", message.chat.id, status_msg.message_id)
             print(f"yt-dlp error: {e}")
             
    finally:
        # Clean up files matching temp_download_{temp_id}
        for f in os.listdir('.'):
            if f.startswith(f"temp_download_{temp_id}"):
                try:
                    os.remove(f)
                except Exception:
                    pass
