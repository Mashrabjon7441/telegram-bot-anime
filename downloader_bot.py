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
    btn_channels = types.KeyboardButton("📢 Homiylar / Kanallar")
    btn_adv = types.KeyboardButton("✉️ Reklama yuborish")
    btn_back = types.KeyboardButton("⬅️ Bosh sahifa")
    keyboard.row(btn_stats, btn_channels)
    keyboard.row(btn_adv, btn_back)
    return keyboard

# --- Channel Subscription Setup ---
def get_unsubscribed_channels(user_id):
    if is_admin(user_id):
        return []
    channels = database.get_mandatory_channels()
    unsubscribed = []
    for ch_id, title, invite_link in channels:
        if not invite_link:
            continue
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

    if call.data.startswith("toggle_ch:"):
        _, ch_id, val = call.data.split(":")
        database.set_channel_mandatory(ch_id, int(val))
        bot.answer_callback_query(call.id, "Holat o'zgartirildi!")
        send_channels_list_menu(call.message.chat.id, call.message.message_id)
        return

    elif call.data == "refresh_ch_list":
        bot.answer_callback_query(call.id, "Yangilandi")
        send_channels_list_menu(call.message.chat.id, call.message.message_id)
        return

    elif call.data == "manual_add_ch":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "Kanalning ID yoki username'ini kiriting (Masalan: -100123456789 yoki @kanal_username):")
        bot.register_next_step_handler(msg, process_channel_id)
        return

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

    if not is_admin(user_id):
        if not check_must_join(message):
            return

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
        msg = bot.send_message(message.chat.id, "Foydalanuvchilarga yubormoqchi bo'lgan reklama xabarini yuboring:\n\nBekor qilish uchun 'bekor' deb yozing.")
        bot.register_next_step_handler(msg, process_adv_message)
        return

    elif text == "📢 Homiylar / Kanallar" and is_admin(user_id):
        send_channels_list_menu(message.chat.id)
        return

    if is_valid_link(text):
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

# --- Channel Manager ---
def send_channels_list_menu(chat_id, edit_message_id=None):
    channels = database.get_admin_channels()
    text = (
        "📢 **Majburiy a'zolik kanallari boshqaruvi**\n\n"
        "Bot admin qilingan kanallar ro'yxati quyida keltirilgan.\n"
        "Tugmani bosish orqali **Majburiy obuna** qilish yoki o'chirish mumkin:\n\n"
        "💡 *Maslahat: Kanalingizga botni qo'shib, adminlik bering. U bu yerda paydo bo'ladi!*"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    if not channels:
        text += "\n\n📭 *Hozircha bot admin qilingan kanallar yo'q.*"
    else:
        for ch_id, title, username, invite, is_mandatory in channels:
            status = "✅ Majburiy obuna" if is_mandatory == 1 else "❌ Majburiy emas"
            btn_text = f"📢 {title} | {status}"
            markup.add(
                types.InlineKeyboardButton(text=btn_text, callback_data=f"toggle_ch:{ch_id}:{1 if is_mandatory == 0 else 0}")
            )
    markup.add(
        types.InlineKeyboardButton(text="➕ Kanalni qo'lda qo'shish", callback_data="manual_add_ch"),
        types.InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_ch_list")
    )
    if edit_message_id:
        try:
            bot.edit_message_text(text, chat_id, edit_message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def process_channel_id(message):
    channel_id = message.text.strip()
    if not channel_id:
        bot.send_message(message.chat.id, "Xato: bo'sh matn yuborildi.")
        return
    msg = bot.send_message(message.chat.id, "Kanal nomini kiriting (Tugmada chiqadigan yozuv):")
    bot.register_next_step_handler(msg, process_channel_title, channel_id)

def process_channel_title(message, channel_id):
    title = message.text.strip()
    if not title:
        bot.send_message(message.chat.id, "Xato: bo'sh yozuv kiritildi.")
        return
    msg = bot.send_message(message.chat.id, "Kanalga taklif havolasini (link) kiriting:")
    bot.register_next_step_handler(msg, process_channel_link, channel_id, title)

def process_channel_link(message, channel_id, title):
    invite_link = message.text.strip()
    if not invite_link:
        bot.send_message(message.chat.id, "Xato: bo'sh link yuborildi.")
        return
    database.save_admin_channel(channel_id, title, username=None, invite_link=invite_link)
    database.set_channel_mandatory(channel_id, 1)
    bot.send_message(message.chat.id, f"✅ Kanal qo'shildi va majburiy obunaga sozlandi!\n\nID: `{channel_id}`\nNomi: {title}\nLink: {invite_link}", parse_mode="Markdown")
    send_channels_list_menu(message.chat.id)

# --- Core Downloader Function ---
def download_and_send_video(message, url):
    status_msg = bot.send_message(message.chat.id, "⏳ Havola tekshirilmoqda va video yuklab olinmoqda... Iltimos kuting...")
    temp_id = str(uuid.uuid4())
    out_tmpl = f"temp_download_{temp_id}.%(ext)s"
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': out_tmpl,
        'max_filesize': 50 * 1024 * 1024,
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
                bot.edit_message_text("❌ Videoni yuklab olishda xatolik yuz berdi yoki video o'lchami (50MB) limitdan katta.", message.chat.id, status_msg.message_id)
    except Exception as e:
        error_msg = str(e)
        if "max-filesize" in error_msg.lower() or "larger than max-filesize" in error_msg.lower():
            bot.edit_message_text("⚠️ **Xatolik:** Ushbu video hajmi o'ta katta (50MB limitidan yuqori).", message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("❌ Yuklab olishda xatolik yuz berdi. Havola to'g'ri yoki ommaga ochiq ekanligini tekshiring.", message.chat.id, status_msg.message_id)
            print(f"yt-dlp error: {e}")
    finally:
        for f in os.listdir('.'):
            if f.startswith(f"temp_download_{temp_id}"):
                try:
                    os.remove(f)
                except Exception:
                    pass

# --- Auto-detect admin channels ---
@bot.my_chat_member_handler()
def my_chat_member_update(update):
    try:
        chat = update.chat
        new_member = update.new_chat_member
        if chat.type == "channel":
            if new_member.status in ["administrator", "creator"]:
                invite_link = None
                try:
                    invite_link = bot.export_chat_invite_link(chat.id)
                except Exception:
                    if chat.username:
                        invite_link = f"https://t.me/{chat.username}"
                database.save_admin_channel(chat.id, chat.title, chat.username, invite_link)
            else:
                database.remove_admin_channel(chat.id)
    except Exception as e:
        print("[Downloader Bot] Error in my_chat_member_handler:", e)
