import telebot
from telebot import types
import requests
import time
from datetime import datetime, timedelta
import logging
import json
import os
from collections import defaultdict

# ========== НАЛАШТУВАННЯ ЛОГУВАННЯ ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Додаткове логування в файл
file_handler = logging.FileHandler('bot_actions.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Токен бота
BOT_TOKEN = '8789801841:AAFFDeT5Zf_w2Fn9j18C7Et5D0O_WL1W1Kg'

# ========== НАЛАШТУВАННЯ ДОСТУПУ ==========
ALLOWED_USERS = [
    1280247828,
    5254643087,
    8585989907,
    8459484659,
    8590894956,
    8357843038,
]

# Файл для збереження даних
DATA_FILE = 'bot_data.json'

def is_user_allowed(user_id):
    return user_id in ALLOWED_USERS

def restricted_access(func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        if not is_user_allowed(user_id):
            bot.send_message(
                message.chat.id,
                "❌ У вас немає доступу до цього бота!"
            )
            return
        return func(message, *args, **kwargs)
    return wrapper

bot = telebot.TeleBot(BOT_TOKEN)

# ========== РОБОТА З ДАНИМИ ==========
def load_data():
    """Завантаження даних з файлу"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Конвертуємо ключі назад у рядки для сумісності
                channels = {}
                for channel_id, channel_data in data.get('channels', {}).items():
                    channels[str(channel_id)] = channel_data
                return {
                    'channels': channels,
                    'current_channel': data.get('current_channel'),
                    'total_links_created': data.get('total_links_created', 0),
                    'total_links_used': data.get('total_links_used', 0),
                    'creation_stats': data.get('creation_stats', {}),
                    'usage_stats': data.get('usage_stats', {})
                }
        except Exception as e:
            logger.error(f"Помилка завантаження даних: {e}")
    
    return {
        'channels': {},
        'current_channel': None,
        'total_links_created': 0,
        'total_links_used': 0,
        'creation_stats': defaultdict(lambda: defaultdict(int)),
        'usage_stats': defaultdict(lambda: defaultdict(int))
    }

def save_data():
    """Збереження даних у файл"""
    try:
        data = {
            'channels': channels,
            'current_channel': current_channel,
            'total_links_created': total_links_created,
            'total_links_used': total_links_used,
            'creation_stats': dict(creation_stats),
            'usage_stats': dict(usage_stats)
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("💾 Дані збережено")
    except Exception as e:
        logger.error(f"❌ Помилка збереження даних: {e}")

# Завантажуємо дані
data = load_data()
channels = data['channels']
current_channel = data['current_channel']
total_links_created = data['total_links_created']
total_links_used = data['total_links_used']
creation_stats = defaultdict(lambda: defaultdict(int), data.get('creation_stats', {}))
usage_stats = defaultdict(lambda: defaultdict(int), data.get('usage_stats', {}))

def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🔗 СТВОРИТИ ПОСИЛАННЯ"),
        types.KeyboardButton("📋 КАНАЛИ")
    )
    keyboard.add(
        types.KeyboardButton("📊 СТАТИСТИКА"),
        types.KeyboardButton("📊 ВСЯ СТАТИСТИКА")
    )
    return keyboard

@bot.message_handler(commands=['start'])
@restricted_access
def start(message):
    global current_channel
    
    welcome_text = "👋 Вітаю!\n\n"
    
    if not channels:
        welcome_text += "📭 У вас немає доданих каналів.\n"
        welcome_text += "Натисніть '📋 КАНАЛИ' щоб додати перший канал.\n\n"
    else:
        if current_channel and current_channel in channels:
            welcome_text += f"✅ Поточний канал: {channels[current_channel]['name']}\n"
        else:
            current_channel = list(channels.keys())[0]
            welcome_text += f"✅ Поточний канал: {channels[current_channel]['name']}\n"
    
    welcome_text += "\n🔹 СТВОРИТИ ПОСИЛАННЯ - створити нові запрошення\n"
    welcome_text += "🔹 КАНАЛИ - додати/змінити канал\n"
    welcome_text += "🔹 СТАТИСТИКА - статистика по посиланнях\n"
    welcome_text += "🔹 ВСЯ СТАТИСТИКА - загальна статистика\n\n"
    welcome_text += "⏰ Термін дії: 10 днів\n"
    welcome_text += "👤 Посилання вимагають НАДІСЛАТИ ЗАПИТ\n"
    welcome_text += "📦 Всі посилання в одному повідомленні\n\n"
    welcome_text += "Оберіть дію нижче 👇"
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

# ========== СТАТИСТИКА ПО ПОСИЛАННЯХ ==========
@bot.message_handler(func=lambda message: message.text == "📊 СТАТИСТИКА")
@restricted_access
def show_stats(message):
    """Показує статистику для кожного посилання"""
    global channels
    
    if not channels:
        bot.send_message(message.chat.id, "📊 Немає каналів для відображення статистики")
        return
    
    # Перевіряємо чи є хоч одне посилання
    has_links = False
    for channel_id, channel_data in channels.items():
        if channel_data.get('links'):
            has_links = True
            break
    
    if not has_links:
        bot.send_message(message.chat.id, "📊 Ще немає створених посилань")
        return
    
    text = "📊 **СТАТИСТИКА ПОСИЛАНЬ**\n"
    text += "══════════════════════\n\n"
    
    for channel_id, channel_data in channels.items():
        channel_links = channel_data.get('links', [])
        
        if not channel_links:
            continue
        
        text += f"**{channel_data['name']}**\n"
        text += "─────────────────\n"
        
        # Сортуємо посилання за номером
        sorted_links = sorted(channel_links, key=lambda x: x.get('number', 0))
        
        for link_data in sorted_links[-50:]:
            name = link_data.get('name', 'Без назви')
            link = link_data.get('link', '')
            
            # Вступило - хто вже в каналі (спочатку)
            joined = len(link_data.get('joined_users', []))
            
            # Заявки - хто подав заявку (очікують) (потім)
            requests = len(link_data.get('pending_users', []))
            
            text += f"{name}\n"
            text += f"{link}\n"
            text += f"(Вступило: {joined} | Заявок: {requests})\n\n"
    
    # Додаємо загальну статистику
    text += "══════════════════════\n"
    text += f"📊 **ЗАГАЛЬНА СТАТИСТИКА**\n"
    text += f"🔗 Всього створено: {total_links_created}\n"
    text += f"✅ Всього вступило: {total_links_used}\n"
    text += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
    
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            bot.send_message(message.chat.id, part)
    else:
        bot.send_message(message.chat.id, text)

# ========== ВСЯ СТАТИСТИКА ==========
@bot.message_handler(func=lambda message: message.text == "📊 ВСЯ СТАТИСТИКА")
@restricted_access
def show_all_stats(message):
    """Показує загальну статистику по всіх каналах"""
    global channels
    
    if not channels:
        bot.send_message(message.chat.id, "📊 Немає каналів для відображення статистики")
        return
    
    text = "📊 **ВСЯ СТАТИСТИКА**\n"
    text += "══════════════════════\n\n"
    
    total_requests_all = 0
    total_joined_all = 0
    total_links_all = 0
    
    for channel_id, channel_data in channels.items():
        channel_links = channel_data.get('links', [])
        channel_name = channel_data['name']
        
        # Підрахунок для каналу
        channel_requests = 0
        channel_joined = 0
        channel_links_count = len(channel_links)
        
        for link_data in channel_links:
            channel_requests += len(link_data.get('pending_users', []))
            channel_joined += len(link_data.get('joined_users', []))
        
        total_requests_all += channel_requests
        total_joined_all += channel_joined
        total_links_all += channel_links_count
        
        text += f"**{channel_name}**\n"
        text += f"├─ 🔗 Посилань: {channel_links_count}\n"
        text += f"├─ ✅ Вступило: {channel_joined}\n"
        text += f"└─ ⏳ Заявок: {channel_requests}\n\n"
    
    text += "══════════════════════\n"
    text += f"**ЗАГАЛОМ**\n"
    text += f"├─ 🔗 Всього посилань: {total_links_all}\n"
    text += f"├─ ✅ Всього вступило: {total_joined_all}\n"
    text += f"└─ ⏳ Всього заявок: {total_requests_all}\n\n"
    text += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    
    bot.send_message(message.chat.id, text)

# ========== КЕРУВАННЯ КАНАЛАМИ ==========
@bot.message_handler(func=lambda message: message.text == "📋 КАНАЛИ")
@restricted_access
def manage_channels(message):
    global channels, current_channel
    
    if not channels:
        text = "📭 У вас немає доданих каналів.\n\nНатисніть '➕ Додати канал' щоб додати перший канал."
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("➕ ДОДАТИ КАНАЛ", callback_data="add_channel"))
        bot.send_message(message.chat.id, text, reply_markup=keyboard)
        return
    
    text = "📋 МОЇ КАНАЛИ\n════════════\n\n"
    if current_channel and current_channel in channels:
        text += f"✅ ПОТОЧНИЙ: {channels[current_channel]['name']}\n\n"
    
    text += "📌 СПИСОК КАНАЛІВ:\n"
    for channel_id, channel_data in channels.items():
        mark = "✅ " if channel_id == current_channel else "• "
        channel_links = len(channel_data.get('links', []))
        text += f"{mark}{channel_data['name']}\n"
        text += f"  └ Посилань: {channel_links}\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for channel_id, channel_data in channels.items():
        if channel_id != current_channel:
            keyboard.add(types.InlineKeyboardButton(
                text=f"📌 {channel_data['name']}",
                callback_data=f"select_{channel_id}"
            ))
    
    keyboard.add(
        types.InlineKeyboardButton("➕ ДОДАТИ КАНАЛ", callback_data="add_channel"),
        types.InlineKeyboardButton("❌ ВИДАЛИТИ КАНАЛ", callback_data="delete_channel")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

# Додавання каналу
@bot.callback_query_handler(func=lambda call: call.data == "add_channel")
@restricted_access
def add_channel(call):
    msg = bot.send_message(
        call.from_user.id,
        "➕ ДОДАВАННЯ КАНАЛУ\n\nВведіть ID каналу:\nНаприклад: -1001234567890\n\n(або '0' для скасування)"
    )
    bot.register_next_step_handler(msg, process_channel_id)
    bot.answer_callback_query(call.id)

def process_channel_id(message):
    if message.text == '0':
        bot.send_message(message.chat.id, "❌ Операцію скасовано", reply_markup=get_main_keyboard())
        return
    
    channel_id = message.text.strip()
    
    if not channel_id.startswith('-100'):
        bot.send_message(
            message.chat.id,
            "❌ Невірний формат!\n\nID має починатися з -100\nНаприклад: -1001234567890"
        )
        return
    
    try:
        chat_info = bot.get_chat(channel_id)
        bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
        
        if bot_member.status not in ['administrator', 'creator']:
            bot.send_message(
                message.chat.id,
                f"❌ Бот не є адміністратором каналу {chat_info.title}!"
            )
            return
        
        if not hasattr(bot_member, 'can_invite_users') or not bot_member.can_invite_users:
            bot.send_message(
                message.chat.id,
                f"❌ Бот не має права запрошувати!"
            )
            return
        
        msg = bot.send_message(
            message.chat.id,
            f"✅ Канал знайдено: {chat_info.title}\n\nВведіть назву для цього каналу:"
        )
        bot.register_next_step_handler(msg, process_channel_name, channel_id, chat_info.title)
        
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Помилка: {str(e)}"
        )

def process_channel_name(message, channel_id, original_name):
    global channels, current_channel
    
    channel_name = message.text.strip()
    if not channel_name or channel_name == '0':
        channel_name = original_name
    
    channels[channel_id] = {
        'name': channel_name,
        'links': []
    }
    
    if len(channels) == 1:
        current_channel = channel_id
    
    save_data()
    
    bot.send_message(
        message.chat.id,
        f"✅ Канал додано!\n\n📌 Назва: {channel_name}\n🆔 ID: {channel_id}",
        reply_markup=get_main_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_"))
@restricted_access
def select_channel(call):
    global current_channel
    channel_id = call.data.replace("select_", "")
    
    if channel_id in channels:
        current_channel = channel_id
        save_data()
        bot.answer_callback_query(call.id, f"✅ Поточний канал: {channels[channel_id]['name']}")
        bot.edit_message_text(f"✅ Поточний канал: {channels[channel_id]['name']}", call.from_user.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "delete_channel")
@restricted_access
def delete_channel_start(call):
    if not channels:
        bot.answer_callback_query(call.id, "Немає каналів для видалення")
        return
    
    text = "❌ ВИДАЛЕННЯ КАНАЛУ\n\nОберіть канал для видалення:"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    for channel_id, channel_data in channels.items():
        keyboard.add(types.InlineKeyboardButton(
            text=f"🗑 {channel_data['name']}",
            callback_data=f"confirm_delete_{channel_id}"
        ))
    
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_channels"))
    
    bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=keyboard)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_"))
@restricted_access
def confirm_delete(call):
    global channels, current_channel
    channel_id = call.data.replace("confirm_delete_", "")
    
    if channel_id in channels:
        channel_name = channels[channel_id]['name']
        
        if current_channel == channel_id:
            remaining = [cid for cid in channels.keys() if cid != channel_id]
            current_channel = remaining[0] if remaining else None
        
        del channels[channel_id]
        save_data()
        
        bot.answer_callback_query(call.id, f"✅ Канал видалено")
        bot.edit_message_text(f"✅ Канал '{channel_name}' видалено!", 
                              call.from_user.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_channels")
@restricted_access
def back_to_channels(call):
    text = "📋 МОЇ КАНАЛИ\n════════════\n\n"
    if current_channel and current_channel in channels:
        text += f"✅ ПОТОЧНИЙ: {channels[current_channel]['name']}\n\n"
    
    text += "📌 СПИСОК КАНАЛІВ:\n"
    for channel_id, channel_data in channels.items():
        mark = "✅ " if channel_id == current_channel else "• "
        channel_links = len(channel_data.get('links', []))
        text += f"{mark}{channel_data['name']}\n"
        text += f"  └ Посилань: {channel_links}\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for channel_id, channel_data in channels.items():
        if channel_id != current_channel:
            keyboard.add(types.InlineKeyboardButton(
                text=f"📌 {channel_data['name']}",
                callback_data=f"select_{channel_id}"
            ))
    
    keyboard.add(
        types.InlineKeyboardButton("➕ ДОДАТИ КАНАЛ", callback_data="add_channel"),
        types.InlineKeyboardButton("❌ ВИДАЛИТИ КАНАЛ", callback_data="delete_channel")
    )
    
    bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=keyboard)
    bot.answer_callback_query(call.id)

# ========== СТВОРЕННЯ ПОСИЛАНЬ ==========
@bot.message_handler(func=lambda message: message.text == "🔗 СТВОРИТИ ПОСИЛАННЯ")
@restricted_access
def create_link_start(message):
    global current_channel
    
    if not channels:
        bot.send_message(
            message.chat.id,
            "❌ Немає каналів!\n\nСпочатку додайте канал через '📋 КАНАЛИ'",
            reply_markup=get_main_keyboard()
        )
        return
    
    if not current_channel or current_channel not in channels:
        current_channel = list(channels.keys())[0]
    
    msg = bot.send_message(
        message.chat.id,
        f"📌 Канал: {channels[current_channel]['name']}\n\n"
        f"🔗 Скільки посилань створити?\n"
        f"Напишіть число (наприклад: 50)\n"
        f"Або '0' для скасування\n\n"
        f"⏰ Термін дії: 10 ДНІВ\n"
        f"👤 КОЖНЕ ПОСИЛАННЯ ВИМАГАЄ НАДІСЛАТИ ЗАПИТ"
    )
    bot.register_next_step_handler(msg, process_link_count)

def process_link_count(message):
    global current_channel, link_count
    
    if message.text == '0':
        bot.send_message(message.chat.id, "❌ Операцію скасовано", reply_markup=get_main_keyboard())
        return
    
    try:
        link_count = int(message.text)
        if link_count <= 0 or link_count > 500:
            bot.send_message(message.chat.id, "❌ Введіть число від 1 до 500", reply_markup=get_main_keyboard())
            return
        
        msg = bot.send_message(
            message.chat.id,
            f"✅ Буде створено {link_count} посилань\n\n"
            f"📝 Введіть назву для посилань:\n"
            f"Наприклад: #2 GR\n\n"
            f"Тоді посилання будуть:\n"
            f"#2 GR 34\n"
            f"#2 GR 35\n"
            f"#2 GR 36\n"
            f"... і так далі\n\n"
            f"Або '0' для скасування"
        )
        bot.register_next_step_handler(msg, process_link_name)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введіть число!", reply_markup=get_main_keyboard())

def process_link_name(message):
    global current_channel, link_count, link_base_name, total_links_created
    
    if message.text == '0':
        bot.send_message(message.chat.id, "❌ Операцію скасовано", reply_markup=get_main_keyboard())
        return
    
    link_base_name = message.text.strip()
    
    if not link_base_name:
        bot.send_message(message.chat.id, "❌ Назва не може бути порожньою!", reply_markup=get_main_keyboard())
        return
    
    status_msg = bot.send_message(
        message.chat.id,
        f"⏳ Створюю {link_count} посилань...\n\n"
        f"📝 Назва: {link_base_name}\n"
        f"⏰ Термін дії: 10 ДНІВ\n"
        f"👤 КОЖНЕ ПОСИЛАННЯ ВИМАГАЄ НАДІСЛАТИ ЗАПИТ\n"
        f"⏱ Орієнтовний час: {link_count * 3} секунд\n\n"
        f"📦 Всі посилання в одному повідомленні"
    )
    
    created_links = []
    channel_data = channels[current_channel]
    
    if 'links' not in channel_data:
        channel_data['links'] = []
    
    # Визначаємо початковий номер
    existing_numbers = []
    for link in channel_data.get('links', []):
        try:
            name_parts = link['name'].split()
            if len(name_parts) > 1 and name_parts[-1].isdigit():
                existing_numbers.append(int(name_parts[-1]))
        except:
            pass
    
    start_number = max(existing_numbers) + 1 if existing_numbers else 1
    
    # Створюємо по 5 посилань з паузою
    batch_size = 5
    batches = (link_count + batch_size - 1) // batch_size
    
    for batch in range(batches):
        start_idx = batch * batch_size
        end_idx = min(start_idx + batch_size, link_count)
        
        bot.edit_message_text(
            f"⏳ Створюю посилання...\n"
            f"📊 Прогрес: {start_idx}/{link_count}\n"
            f"📦 Партія {batch + 1} з {batches}\n"
            f"⏱ Створюю {end_idx - start_idx} посилань...\n"
            f"⏰ Термін: 10 днів",
            message.chat.id,
            status_msg.message_id
        )
        
        for i in range(start_idx, end_idx):
            try:
                link_number = start_number + i
                
                full_name = f"{link_base_name} {link_number}"
                
                # 11 днів в коді = 10 днів покаже Telegram
                expire_date = int((datetime.now() + timedelta(days=11)).timestamp())
                
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/createChatInviteLink"
                # ВАЖЛИВО! creates_join_request = True змушує НАДІСЛАТИ ЗАПИТ
                data = {
                    "chat_id": int(current_channel),
                    "creates_join_request": True,
                    "name": full_name,
                    "expire_date": expire_date
                }
                
                response = requests.post(url, data=data).json()
                
                if response.get("ok"):
                    link = response["result"]["invite_link"]
                    
                    link_data = {
                        'link': link,
                        'name': full_name,
                        'number': link_number,
                        'created_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
                        'pending_users': [],  # Хто подав заявку (очікують)
                        'joined_users': []    # Хто вступив (схвалені)
                    }
                    
                    channel_data['links'].append(link_data)
                    created_links.append(link_data)
                    
                    total_links_created += 1
                    today = datetime.now().strftime('%Y-%m-%d')
                    creation_stats[today][current_channel] += 1
                    
                    logger.info(f"✅ Створено: {full_name} (creates_join_request=True)")
                    
                else:
                    logger.error(f"❌ Помилка: {response}")
                    if response.get('error_code') == 429:
                        retry_after = response.get('parameters', {}).get('retry_after', 30)
                        logger.info(f"⏱ Чекаю {retry_after} секунд...")
                        time.sleep(retry_after)
                    
            except Exception as e:
                logger.error(f"❌ Помилка: {e}")
            
            time.sleep(3)
        
        if batch < batches - 1:
            wait_time = 20
            logger.info(f"⏱ Пауза {wait_time} секунд між партіями...")
            time.sleep(wait_time)
    
    if created_links:
        bot.delete_message(message.chat.id, status_msg.message_id)
        
        delete_date = (datetime.now() + timedelta(days=11)).strftime('%d.%m.%Y %H:%M')
        
        all_links_text = f"🔗 ВСІ ПОСИЛАННЯ ({len(created_links)} шт)\n"
        all_links_text += f"📝 Назва: {link_base_name}\n"
        all_links_text += f"📌 Канал: {channel_data['name']}\n"
        all_links_text += f"⏰ ТЕРМІН ДІЇ: 10 ДНІВ (до {delete_date})\n"
        all_links_text += f"👤 КОЖНЕ ПОСИЛАННЯ ВИМАГАЄ НАДІСЛАТИ ЗАПИТ\n"
        all_links_text += "══════════════════════════\n\n"
        
        for link_data in created_links:
            all_links_text += f"📌 {link_data['name']}\n"
            all_links_text += f"🔗 {link_data['link']}\n\n"
        
        if len(all_links_text) > 4000:
            parts = []
            current_part = f"🔗 ПОСИЛАННЯ (частина 1)\n{link_base_name}\n⏰ Термін: 10 днів\n══════════════════════════\n\n"
            
            for i, link_data in enumerate(created_links, 1):
                link_text = f"📌 {link_data['name']}\n{link_data['link']}\n\n"
                if len(current_part) + len(link_text) > 4000:
                    parts.append(current_part)
                    current_part = f"🔗 ПОСИЛАННЯ (частина {len(parts)+1})\n{link_base_name}\n⏰ Термін: 10 днів\n══════════════════════════\n\n"
                current_part += link_text
            
            if current_part:
                parts.append(current_part)
            
            for i, part in enumerate(parts, 1):
                bot.send_message(message.chat.id, part)
                time.sleep(1)
        else:
            bot.send_message(message.chat.id, all_links_text)
        
        stats_text = f"📊 СТАТИСТИКА СТВОРЕННЯ:\n\n"
        stats_text += f"📝 Назва: {link_base_name}\n"
        stats_text += f"🔗 Створено: {len(created_links)} посилань\n"
        stats_text += f"📌 Всього в каналі: {len(channel_data['links'])}\n"
        stats_text += f"👤 Всі посилання вимагають НАДІСЛАТИ ЗАПИТ\n"
        stats_text += f"📊 Загальна статистика:\n"
        stats_text += f"├─ Всього створено: {total_links_created}\n"
        stats_text += f"└─ Всього використано: {total_links_used}\n"
        stats_text += f"⏰ Термін дії: 10 днів\n"
        stats_text += f"📅 Дійсні до: {delete_date}\n"
        stats_text += f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        bot.send_message(message.chat.id, stats_text)
        
        save_data()
        
    else:
        bot.edit_message_text(
            "❌ Не вдалося створити жодного посилання!",
            message.chat.id,
            status_msg.message_id
        )

# ========== ФУНКЦІЇ ДЛЯ ВІДСТЕЖЕННЯ ==========
def track_pending_request(link, user_id, user_name):
    """Відстежує подання заявки (очікує схвалення)"""
    logger.info(f"🔍 track_pending_request викликано: link={link}, user_id={user_id}, user_name={user_name}")
    
    for channel_id, channel_data in channels.items():
        for link_data in channel_data.get('links', []):
            if link_data['link'] == link:
                logger.info(f"✅ Знайдено посилання: {link_data['name']}")
                
                # Додаємо в список очікуючих
                if 'pending_users' not in link_data:
                    link_data['pending_users'] = []
                
                # Перевіряємо чи вже є в списку
                user_exists = False
                for user in link_data['pending_users']:
                    if user.get('id') == user_id:
                        user_exists = True
                        break
                
                if not user_exists:
                    link_data['pending_users'].append({
                        'id': user_id,
                        'name': user_name,
                        'time': datetime.now().strftime('%d.%m.%Y %H:%M')
                    })
                    
                    logger.info(f"📝 НОВА ЗАЯВКА!")
                    logger.info(f"   Ім'я: {user_name}")
                    logger.info(f"   ID: {user_id}")
                    logger.info(f"   Посилання: {link_data['name']}")
                    logger.info(f"   Статус: Очікує схвалення")
                    logger.info(f"📊 Заявок в черзі: {len(link_data['pending_users'])}")
                    logger.info("-" * 50)
                    
                    save_data()
                else:
                    logger.info(f"⚠️ Користувач {user_id} вже в списку очікуючих")
                
                return True
    
    logger.warning(f"❌ Посилання не знайдено: {link}")
    return False

def track_user_joined(link, user_id, user_name=None):
    """Відстежує коли заявку СХВАЛЕНО і користувач вступив"""
    global total_links_used, usage_stats
    
    logger.info(f"🔍 track_user_joined викликано: link={link}, user_id={user_id}, user_name={user_name}")
    
    for channel_id, channel_data in channels.items():
        for link_data in channel_data.get('links', []):
            if link_data['link'] == link:
                logger.info(f"✅ Знайдено посилання: {link_data['name']}")
                
                # Додаємо в список тих хто вступив
                if 'joined_users' not in link_data:
                    link_data['joined_users'] = []
                
                # Перевіряємо чи вже є в списку
                user_exists = False
                for user in link_data['joined_users']:
                    if user.get('id') == user_id:
                        user_exists = True
                        break
                
                if not user_exists:
                    # Додаємо інформацію про користувача
                    user_info = {
                        'id': user_id,
                        'name': user_name or f"ID:{user_id}",
                        'time': datetime.now().strftime('%d.%m.%Y %H:%M')
                    }
                    link_data['joined_users'].append(user_info)
                    
                    # ВАЖЛИВО! Видаляємо з очікуючих
                    if 'pending_users' in link_data:
                        old_count = len(link_data['pending_users'])
                        link_data['pending_users'] = [u for u in link_data['pending_users'] if u.get('id') != user_id]
                        logger.info(f"📊 Видалено з очікуючих: {old_count} -> {len(link_data['pending_users'])}")
                    
                    # Оновлюємо статистику
                    total_links_used += 1
                    today = datetime.now().strftime('%Y-%m-%d')
                    usage_stats[today][channel_id] += 1
                    
                    logger.info(f"✅ ЗАЯВКУ СХВАЛЕНО!")
                    logger.info(f"   Ім'я: {user_name}")
                    logger.info(f"   ID: {user_id}")
                    logger.info(f"   Посилання: {link_data['name']}")
                    logger.info(f"   Статус: Вступив в канал")
                    logger.info(f"📊 Заявок в черзі: {len(link_data.get('pending_users', []))}")
                    logger.info(f"📊 Всього вступило: {len(link_data['joined_users'])}")
                    logger.info("-" * 50)
                    
                    save_data()
                else:
                    logger.info(f"⚠️ Користувач {user_id} вже в списку тих хто вступив")
                
                return True
    
    logger.warning(f"❌ Посилання не знайдено: {link}")
    return False

# ========== ВІДСТЕЖЕННЯ ЗАЯВОК ==========
@bot.chat_join_request_handler()
def handle_join_request(update):
    try:
        logger.info("=" * 60)
        logger.info("🔥 ОТРИМАНО ЗАПИТ НА ВСТУП")
        logger.info(f"   Chat ID: {update.chat.id}")
        logger.info(f"   User ID: {update.from_user.id}")
        logger.info(f"   User name: {update.from_user.first_name}")
        
        if update.invite_link:
            used_link = update.invite_link.invite_link
            user = update.from_user
            user_id = user.id
            user_name = user.first_name or user.username or f"ID:{user_id}"

            logger.info(f"   Посилання: {used_link}")
            
            # Відстежуємо заявку
            track_pending_request(used_link, user_id, user_name)
        
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ ПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()

# ========== ВІДСТЕЖЕННЯ ВХОДІВ В КАНАЛ ==========
@bot.chat_member_handler()
def handle_chat_member(update):
    try:
        logger.info("=" * 60)
        logger.info("🔥 ОТРИМАНО ОНОВЛЕННЯ CHAT_MEMBER")
        logger.info(f"   Chat ID: {update.chat.id}")
        logger.info(f"   Old status: {update.old_chat_member.status}")
        logger.info(f"   New status: {update.new_chat_member.status}")
        
        if update.invite_link:
            logger.info(f"   Invite link: {update.invite_link.invite_link}")
        
        # ЗМІНЕНО! Тепер просто перевіряємо чи статус member
        if update.new_chat_member.status == "member":
            logger.info("✅ КОРИСТУВАЧ СТАВ УЧАСНИКОМ КАНАЛУ")
            
            invite = update.invite_link
            if invite:
                used_link = invite.invite_link
                user = update.new_chat_member.user
                user_id = user.id
                user_name = user.first_name or user.username or f"ID:{user_id}"

                logger.info(f"   Ім'я: {user_name}")
                logger.info(f"   ID: {user_id}")
                logger.info(f"   Посилання: {used_link}")

                track_user_joined(used_link, user_id, user_name)
        else:
            logger.info(f"   Інша зміна статусу: {update.old_chat_member.status} -> {update.new_chat_member.status}")
        
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ ПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()

# Запуск бота
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 БОТ ЗАПУЩЕНО!")
    print("=" * 60)
    print("📌 ДОЗВОЛЕНІ КОРИСТУВАЧІ:")
    for i, user_id in enumerate(ALLOWED_USERS, 1):
        print(f"{i}. ID: {user_id}")
    print("=" * 60)
    print("📊 СТАТИСТИКА:")
    print(f"   Всього створено посилань: {total_links_created}")
    print(f"   Всього вступило: {total_links_used}")
    print(f"   Каналів: {len(channels)}")
    print("=" * 60)
    print("✅ НАЛАШТУВАННЯ:")
    print("   • Термін дії: 10 ДНІВ")
    print("   • КОЖНЕ ПОСИЛАННЯ ВИМАГАЄ НАДІСЛАТИ ЗАПИТ")
    print("   • ЛОГИ ЗБЕРІГАЮТЬСЯ В ФАЙЛ bot_actions.log")
    print("=" * 60)
    print("📊 НОВА КНОПКА:")
    print("   • 📊 СТАТИСТИКА - статистика по кожному посиланню")
    print("   • 📊 ВСЯ СТАТИСТИКА - загальна статистика по каналах")
    print("=" * 60)
    
    bot.remove_webhook()
    print("🔄 Бот запускається...")
    print("📝 ЧЕКАЮ НА ЗАЯВКИ...")
    
    # ВАЖЛИВО! Додано chat_join_request в allowed_updates
    bot.infinity_polling(
        timeout=60,
        long_polling_timeout=60,
        allowed_updates=["chat_member", "message", "callback_query", "chat_join_request"]
    )