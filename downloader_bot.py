import telebot
from telebot import types
import os
import yt_dlp
import threading
import uuid
import config
import database

bot = telebot.TeleBot(config.DOWNLOADER_BOT_TOKEN)

# --- Admin Helpers ---
def is_admin(user_id):
    return user_id in config.ADMIN_IDS

# --- Keyboards ---
def get_main_keyboard(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if is_admin(user_id):
        btn_admin = types.KeyboardButton("⚙️ Admin panel")
        keyboard.add(btn_admin)
    return keyboard

def get_admin_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_stats = types.KeyboardButton("📊 Statistika")
    btn_adv = types.KeyboardButton("✉️ Reklama yuborish")
    btn_back = types.KeyboardButton("⬅️ Bosh sahifa")
    keyboard.row(btn_stats, btn_adv)
    keyboard.row(btn_back)
    return keyboard

# --- Channel Subscription Setup ---
def get_unsubscribed_channels(user_id):
    if is_admin(user_id):
        return []
    
    channels = database.get_channels()
    unsubscribed = []
    
    for ch_id, title, invite_link in channels:
        try:
            res = bot.get_chat_member(ch_id, user_id)
            if res.status in ['left', 'kicked']:
                unsubscribed.append((title, invite_link))
        except Exception as e:
            print(f"[Downloader Bot] Chat status check error for {ch_id}: {e}")
            
    return unsubscribed

def check_must_join(message):
    unsubscribed = get_unsubscribed_channels(message.from_user.id)
    if unsubscribed:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for title, invite_link in unsubscribed:
            markup.add(types.InlineKeyboardButton(text=f"📢 {title}", url=invite_link))
        
        markup.add(types.InlineKeyboardButton(text="🔄 Tasdiqlash", callback_data="check_sub"))
        
        bot.send_message(
            message.chat.id,
            "⚠️ **Botdan foydalanish uchun quyidagi homiy kanallariga a'zo bo'lishingiz zarur:**\n\nA'zo bo'lgach, *Tasdiqlash* tugmasini bosing.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return False
    return True

# --- Link Helper ---
def is_valid_link(text):
    text = text.lower().strip()
    return any(domain in text for domain in [
        'youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com', 
        'facebook.com', 'fb.watch', 'twitter.com', 'x.com', 'pinterest.com'
    ])

# --- /start Command ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    username = message.from_user.username
    database.add_downloader_user(user_id, username)
    
    if not check_must_join(message):
        return
            
    welcome_text = (
        f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
        "🤖 Ijtimoiy tarmoqlardan video yuklovchi botga xush kelibsiz!\n"
        "Menga videoning havolasini yuboring (Reels, Shorts, Video, TikTok), men uni sizga yuklab beraman.\n\n"
        "Qo'llab-quvvatlanadigan tarmoqlar:\n"
        "• YouTube, Instagram, TikTok, Facebook, Pinterest va Twitter/X"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(user_id))

# --- Callback Handler ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    if call.data == "check_sub":
        unsubscribed = get_unsubscribed_channels(user_id)
        if unsubscribed:
            bot.answer_callback_query(call.id, "❌ Siz hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "✅ Muvaffaqiyatli a'zo bo'ldingiz! Endi botdan foydalanishingiz mumkin.", show_alert=True)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            welcome_text = (
                f"Assalomu alaykum, {call.from_user.first_name}!\n\n"
                "🤖 Ijtimoiy tarmoqlardan video yuklovchi botga xush kelibsiz!\n"
                "Menga videoning havolasini yuboring, men uni sizga yuklab beraman."
            )
            bot.send_message(call.message.chat.id, welcome_text, reply_markup=get_main_keyboard(user_id))
            
    elif call.data.startswith("send_adv:"):
        _, from_chat_id, msg_id = call.data.split(":")
        from_chat_id = int(from_chat_id)
        msg_id = int(msg_id)
        
        bot.answer_callback_query(call.id, "Reklama yuborish boshlandi...")
        bot.edit_message_text("Reklama barchaga yuborilmoqda... Iltimos kuting...", call.message.chat.id, call.message.message_id)
        
        users = database.get_downloader_users()
        success_count = 0
        fail_count = 0
        
        for u_id in users:
            try:
                bot.copy_message(chat_id=u_id, from_chat_id=from_chat_id, message_id=msg_id)
                success_count += 1
            except Exception as e:
                print(f"[Downloader Bot] Ad delivery fail for {u_id}: {e}")
                fail_count += 1
                
        status_text = (
            f"📢 **Reklama tarqatish yakunlandi!**\n\n"
            f"✅ Yetkazildi: {success_count} ta foydalanuvchiga\n"
            f"❌ Yuborilmadi (bloklaganlar): {fail_count} ta"
        )
        bot.send_message(call.message.chat.id, status_text, parse_mode="Markdown", reply_markup=get_admin_keyboard())
        
    elif call.data == "cancel_adv":
        bot.answer_callback_query(call.id, "Bekor qilindi")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Reklama yuborish bekor qilindi.", reply_markup=get_admin_keyboard())

# --- Text Handler ---
@bot.message_handler(func=lambda msg: True)
def text_handler(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Check subscription first
    if not is_admin(user_id):
        if not check_must_join(message):
            return
            
    # Admin commands check
    if text == "⚙️ Admin panel" and is_admin(user_id):
        bot.send_message(message.chat.id, "Admin panelga xush kelibsiz. Amalni tanlang:", reply_markup=get_admin_keyboard())
        return
        
    elif text == "⬅️ Bosh sahifa":
        bot.send_message(message.chat.id, "Bosh sahifaga qaytdingiz.", reply_markup=get_main_keyboard(user_id))
        return
        
    elif text == "📊 Statistika" and is_admin(user_id):
        count = database.get_downloader_users_count()
        bot.send_message(message.chat.id, f"📊 Bot faol a'zolari soni (downloader): {count} ta")
        return
        
    elif text == "✉️ Reklama yuborish" and is_admin(user_id):
        msg = bot.send_message(message.chat.id, "Foydalanuvchilarga yubormoqchi bo'lgan reklama xabarini yuboring (Matn, rasm, video yoki audio):\n\nBekor qilish uchun 'bekor' deb yozing.")
        bot.register_next_step_handler(msg, process_adv_message)
        return

    # Normal Link Download Check
    if is_valid_link(text):
        # Process downloader workflow
        t = threading.Thread(target=download_and_send_video, args=(message, text))
        t.start()
    else:
        bot.send_message(message.chat.id, "❌ Noma'lum buyruq yoki xato havola. Iltimos, video havolasini yuboring!")

# --- Advertising Workflow ---
def process_adv_message(message):
    if message.text and message.text.lower() == 'bekor':
        bot.send_message(message.chat.id, "Reklama yuborish bekor qilindi.", reply_markup=get_admin_keyboard())
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"send_adv:{message.chat.id}:{message.message_id}"),
        types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_adv")
    )
    bot.send_message(message.chat.id, "⚠️ Ushbu xabarni barcha video yuklovchi foydalanuvchilariga tarqatishni tasdiqlaysizmi?", reply_markup=markup)

# --- Core Downloader Function ---
def download_and_send_video(message, url):
    status_msg = bot.send_message(message.chat.id, "⏳ Havola tekshirilmoqda va video yuklab olinmoqda... Iltimos kuting...")
    
    temp_id = str(uuid.uuid4())
    out_tmpl = f"temp_download_{temp_id}.%(ext)s"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': out_tmpl,
        'max_filesize': 50 * 1024 * 1024, # limit to 50MB
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            downloaded_file = filename
            if not os.path.exists(downloaded_file):
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
        for f in os.listdir('.'):
            if f.startswith(f"temp_download_{temp_id}"):
                try:
                    os.remove(f)
                except Exception:
                    pass
