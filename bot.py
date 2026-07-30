import telebot
import random
import json
import os
import time
from datetime import datetime, timedelta
from telebot import types

# --- НАСТРОЙКИ ---
TOKEN = "8421479187:AAHv5P6bADrmHLw9czEYsqP-MRIVC9n6XGs"
ADMIN_USERNAME = "Iadec"
bot = telebot.TeleBot(TOKEN)

DATA_FILE = 'card_data.json'
PLAYERS_FILE = 'players_data.json'
IMG_FOLDER = 'cards_img'

if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)

# --- ФУНКЦИИ СОХРАНЕНИЯ ---
def save_data(data, filename):
    attempts = 0
    while attempts < 10:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return
        except PermissionError:
            attempts += 1
            time.sleep(0.5)

def load_data(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

# --- НАСТРОЙКИ РЕДКОСТЕЙ ---
RARITY_SETTINGS = {
    "Редкая": {"points": 1, "money": 5, "chance": 70},
    "Сверхредкая": {"points": 2, "money": 15, "chance": 20},
    "Эпическая": {"points": 3, "money": 40, "chance": 7},
    "Мифическая": {"points": 4, "money": 100, "chance": 2.5},
    "Легендарка": {"points": 5, "money": 250, "chance": 0.5}
}

# --- УНИВЕРСАЛЬНЫЕ ФУНКЦИИ ---
def get_card_name(card):
    if isinstance(card, dict) and 'name' in card:
        return card['name']
    elif isinstance(card, str):
        return card
    return "Неизвестная карта"

def get_card_rarity(card):
    if isinstance(card, dict) and 'rarity' in card:
        return card['rarity']
    return "Редкая"

# --- ФУНКЦИЯ ВЫДАЧИ КАРТЫ ---
def give_card_to_user(user_id, username, chat_id, specific_rarity=None):
    cards_db = load_data(DATA_FILE)
    if not cards_db:
        return False, "❌ Колода пуста! Админ ещё не добавил карты."
    
    players_db = load_data(PLAYERS_FILE)
    if user_id not in players_db:
        players_db[user_id] = {'username': username, 'points': 0, 'money': 0, 'cards_received': []}

    if specific_rarity:
        chosen_rarity = specific_rarity
    else:
        rarity_names = list(RARITY_SETTINGS.keys())
        rarity_weights = [RARITY_SETTINGS[r]['chance'] for r in rarity_names]
        chosen_rarity = random.choices(rarity_names, weights=rarity_weights, k=1)[0]
    
    available_cards = [c_id for c_id, info in cards_db.items() if info['rarity'] == chosen_rarity]
    if not available_cards:
        available_cards = list(cards_db.keys())
        
    card_id = random.choice(available_cards)
    card_info = cards_db[card_id]
    rarity_stats = RARITY_SETTINGS[card_info['rarity']]
    
    players_db[user_id]['points'] += rarity_stats['points']
    players_db[user_id]['money'] += rarity_stats['money']
    
    players_db[user_id]['cards_received'].append({
        'card_id': card_id,
        'name': card_info['name'],
        'rarity': card_info['rarity']
    })
    
    save_data(players_db, PLAYERS_FILE)
    
    try:
        with open(card_info['img_path'], 'rb') as img_file:
            caption = (
                f"🎴 Название: **{card_info['name']}**\n"
                f"💎 Редкость: **{card_info['rarity']}** 🔥\n"
                f"✨ Очки: +{rarity_stats['points']}  |  💰 Монеты: +{rarity_stats['money']}\n\n"
                f"👤 Выпало: @{username}"
            )
            bot.send_photo(chat_id, img_file, caption=caption, parse_mode='Markdown')
        return True, None
    except Exception as e:
        return False, "⚠️ Ошибка отправки картинки."

# ------------------ КОМАНДЫ И МЕНЮ ------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    if message.chat.type == 'private':
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn0 = types.InlineKeyboardButton("🃏 Открыть карту", callback_data="menu_open")
        btn1 = types.InlineKeyboardButton("🎁 Магазин", callback_data="menu_shop")
        btn2 = types.InlineKeyboardButton("🃏 Мои карты", callback_data="menu_profile")
        btn3 = types.InlineKeyboardButton("📋 Топ", callback_data="menu_top")
        btn4 = types.InlineKeyboardButton("⚔️ Дуэль", callback_data="menu_fight")
        btn5 = types.InlineKeyboardButton("➕ Добавить карту", callback_data="menu_add")
        markup.add(btn0, btn1, btn2, btn3, btn4, btn5)
        bot.send_message(message.chat.id, f"👋 Привет, **{message.from_user.first_name}**!\n\n🃏 Нажми кнопку, чтобы открыть карту, или напиши **годжик**.\n💰 Копи монеты и покупай наборы в магазине!", parse_mode='Markdown', reply_markup=markup)
    else:
        bot.reply_to(message, "👋 Напиши мне в ЛС для управления.")

@bot.message_handler(commands=['addcard'])
def add_card_start(message):
    if message.chat.type == 'private' and message.from_user.username == ADMIN_USERNAME:
        msg = bot.reply_to(message, "📝 Введи **название** карты:")
        user_temp_data[message.chat.id] = {'step': 'name'}
        bot.register_next_step_handler(msg, process_name_step)

def process_name_step(message):
    if message.text is None:
        msg = bot.reply_to(message, "❌ Это не текст!")
        bot.register_next_step_handler(msg, process_name_step)
        return
    user_temp_data[message.chat.id]['name'] = message.text
    msg = bot.reply_to(message, "💎 Введи **редкость** (Редкая, Сверхредкая, Эпическая, Мифическая, Легендарка):")
    bot.register_next_step_handler(msg, process_rarity_step)

def process_rarity_step(message):
    if message.text is None:
        msg = bot.reply_to(message, "❌ Это не текст!")
        bot.register_next_step_handler(msg, process_rarity_step)
        return
    rarity = message.text.strip()
    if rarity not in RARITY_SETTINGS:
        msg = bot.reply_to(message, "❌ Нет такой редкости!")
        bot.register_next_step_handler(msg, process_rarity_step)
        return
    user_temp_data[message.chat.id]['rarity'] = rarity
    msg = bot.reply_to(message, "🖼️ Отправь картинку:")
    bot.register_next_step_handler(msg, process_image_step)

def process_image_step(message):
    if message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        user_data = user_temp_data[message.chat.id]
        card_name, card_rarity = user_data['name'], user_data['rarity']
        cards_db = load_data(DATA_FILE)
        new_id = str(len(cards_db) + 1)
        img_path = os.path.join(IMG_FOLDER, f"{new_id}.jpg")
        with open(img_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        cards_db[new_id] = {'name': card_name, 'rarity': card_rarity, 'img_path': img_path}
        save_data(cards_db, DATA_FILE)
        bot.reply_to(message, f"✅ Карта **{card_name}** ({card_rarity}) сохранена под ID {new_id}!")
        del user_temp_data[message.chat.id]
    else:
        msg = bot.reply_to(message, "❌ Это не картинка!")
        bot.register_next_step_handler(msg, process_image_step)

# ------------------ ОБРАБОТЧИКИ МЕНЮ (ВСЕГДА ОТПРАВЛЯЕМ НОВОЕ) ------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def menu_callback(call):
    bot.answer_callback_query(call.id)
    
    if call.data == "menu_open":
        fake_message = call.message
        fake_message.text = "годжик"
        get_card_main(fake_message)

    elif call.data == "menu_shop":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn1 = types.InlineKeyboardButton("1. 🎁 Набор «Новичок» (50💰)", callback_data="buy_1")
        btn2 = types.InlineKeyboardButton("2. 🟢 Набор «Редкая» (100💰)", callback_data="buy_2")
        btn3 = types.InlineKeyboardButton("3. 🔵 Набор «Эпическая» (300💰)", callback_data="buy_3")
        btn4 = types.InlineKeyboardButton("4. 🟠 Набор «Мифическая» (700💰)", callback_data="buy_4")
        btn5 = types.InlineKeyboardButton("5. 🔴 Набор «Легендарка» (2000💰)", callback_data="buy_5")
        btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")
        markup.add(btn1, btn2, btn3, btn4, btn5, btn_back)
        bot.send_message(call.message.chat.id, "🛒 **МАГАЗИН КАРТ**\n\nВыбери набор, который хочешь открыть:", parse_mode='Markdown', reply_markup=markup)

    elif call.data == "menu_profile":
        user_id = str(call.from_user.id)
        players_db = load_data(PLAYERS_FILE)
        if user_id not in players_db:
            bot.send_message(call.message.chat.id, "👤 У тебя пока нет карт! Напиши **годжик** чтобы начать.")
            return
        show_profile_text(call.message)
        
    elif call.data == "menu_top":
        show_top_text(call.message)
        
    elif call.data == "menu_fight":
        bot.send_message(call.message.chat.id, "⚔️ Чтобы вызвать на дуэль, напиши в чат команду:\n`/fight @ник_соперника`", parse_mode='Markdown')
        
    elif call.data == "menu_add":
        if call.from_user.username == ADMIN_USERNAME:
            bot.send_message(call.message.chat.id, "➕ Чтобы добавить карту, напиши команду `/addcard`", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ Эта функция только для админа!")

# Функции для отправки текста (всегда новым сообщением, без Markdown)
def show_profile_text(message):
    user_id = str(message.chat.id)
    players_db = load_data(PLAYERS_FILE)
    data = players_db[user_id]
    total_cards = len(data['cards_received'])
    cards_list = ""
    if total_cards > 0:
        last_cards = data['cards_received'][-20:]
        for card in last_cards:
            cards_list += f"🃏 {get_card_name(card)}\n"
        if total_cards > 20:
            cards_list += f"\n...и ещё {total_cards - 20} карт скрыто."
    else:
        cards_list = "Пока пусто..."
    text = (
        f"📊 ПРОФИЛЬ ИГРОКА\n"
        f"👤 Имя: {message.from_user.first_name}\n"
        f"⭐ Очки: {data['points']}\n"
        f"💰 Монеты: {data['money']}\n"
        f"🃏 Всего карт в коллекции: {total_cards}\n\n"
        f"📜 Ваши карты (последние 20):\n"
        f"{cards_list}"
    )
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")
    markup.add(btn_back)
    bot.send_message(message.chat.id, text, reply_markup=markup)

def show_top_text(message):
    players_db = load_data(PLAYERS_FILE)
    if not players_db:
        bot.send_message(message.chat.id, "📊 Пока никто не играл.")
        return
    sorted_players = sorted(players_db.items(), key=lambda x: x[1]['money'], reverse=True)[:5]
    text = "🏆 ТОП-5 БОГАЧЕЙ\n\n"
    for i, (uid, data) in enumerate(sorted_players, 1):
        name = data['username'] or "Аноним"
        text += f"{i}. @{name} — 💰 {data['money']} монет\n"
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")
    markup.add(btn_back)
    bot.send_message(message.chat.id, text, reply_markup=markup)

# ------------------ ПОКУПКИ ------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_callback(call):
    bot.answer_callback_query(call.id)
    user_id = str(call.from_user.id)
    players_db = load_data(PLAYERS_FILE)
    if user_id not in players_db:
        players_db[user_id] = {'username': call.from_user.username or "Аноним", 'points': 0, 'money': 0, 'cards_received': []}

    shop_map = {
        "buy_1": {"rarity": None, "price": 50, "name": "🎁 Набор «Новичок»"},
        "buy_2": {"rarity": "Редкая", "price": 100, "name": "🟢 Набор «Редкая»"},
        "buy_3": {"rarity": "Эпическая", "price": 300, "name": "🔵 Набор «Эпическая»"},
        "buy_4": {"rarity": "Мифическая", "price": 700, "name": "🟠 Набор «Мифическая»"},
        "buy_5": {"rarity": "Легендарка", "price": 2000, "name": "🔴 Набор «Легендарка»"}
    }

    item = shop_map.get(call.data)
    if not item:
        return

    if players_db[user_id]['money'] < item['price']:
        bot.send_message(call.message.chat.id, f"❌ Не хватает монет! Нужно {item['price']}💰")
        return

    players_db[user_id]['money'] -= item['price']
    save_data(players_db, PLAYERS_FILE)

    bot.send_message(call.message.chat.id, f"🎉 Открываю {item['name']}...")
    success, error = give_card_to_user(user_id, call.from_user.username or "Аноним", call.message.chat.id, item['rarity'])

# ------------------ ОБРАБОТЧИК КНОПКИ "НАЗАД" ------------------
@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn0 = types.InlineKeyboardButton("🃏 Открыть карту", callback_data="menu_open")
    btn1 = types.InlineKeyboardButton("🎁 Магазин", callback_data="menu_shop")
    btn2 = types.InlineKeyboardButton("🃏 Мои карты", callback_data="menu_profile")
    btn3 = types.InlineKeyboardButton("📋 Топ", callback_data="menu_top")
    btn4 = types.InlineKeyboardButton("⚔️ Дуэль", callback_data="menu_fight")
    btn5 = types.InlineKeyboardButton("➕ Добавить карту", callback_data="menu_add")
    markup.add(btn0, btn1, btn2, btn3, btn4, btn5)
    bot.send_message(call.message.chat.id, f"👋 Привет, {call.from_user.first_name}!\n\n🃏 Нажми кнопку, чтобы открыть карту, или напиши годжик.\n💰 Копи монеты и покупай наборы в магазине!", reply_markup=markup)

# ------------------ КОМАНДЫ ДЛЯ ВСЕХ ------------------
@bot.message_handler(commands=['profile'])
def profile_cmd(message):
    user_id = str(message.from_user.id)
    username = message.from_user.first_name or "Игрок"
    players_db = load_data(PLAYERS_FILE)
    if user_id not in players_db:
        bot.reply_to(message, "👤 У тебя пока нет карт! Напиши **годжик** чтобы начать.")
        return
    data = players_db[user_id]
    total_cards = len(data['cards_received'])
    cards_list = ""
    if total_cards > 0:
        last_cards = data['cards_received'][-20:]
        for card in last_cards:
            cards_list += f"🃏 {get_card_name(card)}\n"
        if total_cards > 20:
            cards_list += f"\n...и ещё {total_cards - 20} карт скрыто."
    else:
        cards_list = "Пока пусто..."
    text = (
        f"📊 ПРОФИЛЬ ИГРОКА\n"
        f"👤 Имя: {username}\n"
        f"⭐ Очки: {data['points']}\n"
        f"💰 Монеты: {data['money']}\n"
        f"🃏 Всего карт в коллекции: {total_cards}\n\n"
        f"📜 Ваши карты (последние 20):\n"
        f"{cards_list}"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['top'])
def top_cmd(message):
    players_db = load_data(PLAYERS_FILE)
    if not players_db:
        bot.reply_to(message, "📊 Пока никто не играл.")
        return
    sorted_players = sorted(players_db.items(), key=lambda x: x[1]['money'], reverse=True)[:5]
    text = "🏆 ТОП-5 БОГАЧЕЙ\n\n"
    for i, (uid, data) in enumerate(sorted_players, 1):
        name = data['username'] or "Аноним"
        text += f"{i}. @{name} — 💰 {data['money']} монет\n"
    bot.reply_to(message, text)

@bot.message_handler(commands=['daily'])
def daily_cmd(message):
    user_id = str(message.from_user.id)
    players_db = load_data(PLAYERS_FILE)
    if user_id not in players_db:
        players_db[user_id] = {'username': message.from_user.username or "Аноним", 'points': 0, 'money': 0, 'cards_received': [], 'last_daily': None}
    today = datetime.now().strftime("%Y-%m-%d")
    if players_db[user_id].get('last_daily') == today:
        bot.reply_to(message, "⏳ Ты уже получил бонус сегодня! Возвращайся завтра.")
        return
    players_db[user_id]['points'] += 5
    players_db[user_id]['money'] += 10
    players_db[user_id]['last_daily'] = today
    save_data(players_db, PLAYERS_FILE)
    bot.reply_to(message, "🎁 Ежедневный бонус получен! +5 очков и +10 монет!")

@bot.message_handler(commands=['sell'])
def sell_cmd(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Пример: `/sell НазваниеКарты`")
        return
    target_card_name = args[1]
    user_id = str(message.from_user.id)
    players_db = load_data(PLAYERS_FILE)
    if user_id not in players_db:
        bot.reply_to(message, "У тебя нет карт.")
        return
    card_found = None
    for card in players_db[user_id]['cards_received']:
        if get_card_name(card).lower() == target_card_name.lower():
            card_found = card
            break
    if not card_found:
        bot.reply_to(message, "У тебя нет этой карты в коллекции.")
        return
    card_rarity = get_card_rarity(card_found)
    rarity_info = RARITY_SETTINGS.get(card_rarity, {})
    sell_price = rarity_info.get('money', 0) // 2
    players_db[user_id]['cards_received'].remove(card_found)
    players_db[user_id]['money'] += sell_price
    save_data(players_db, PLAYERS_FILE)
    bot.reply_to(message, f"🏪 Ты продал карту **{target_card_name}** за **{sell_price}** монет!")

# ------------------ ФУНКЦИЯ "ГОДЖИК" (ГРУППА И ЛС) ------------------
@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() == "годжик")
def get_card_main(message):
    if message.from_user.id == bot.get_me().id:
        return

    user_id = str(message.from_user.id)
    username = message.from_user.username or "Аноним"
    chat_id = message.chat.id
    
    players_db = load_data(PLAYERS_FILE)
    
    if user_id in players_db and 'last_godzik_time' in players_db[user_id]:
        last_time = datetime.fromisoformat(players_db[user_id]['last_godzik_time'])
        if datetime.now() < last_time + timedelta(hours=1):
            remaining = (last_time + timedelta(hours=1) - datetime.now())
            minutes = remaining.seconds // 60
            seconds = remaining.seconds % 60
            bot.reply_to(message, f"Годжик ушёл в тень...\n⏳ Подожди ещё {minutes} мин {seconds} сек.")
            return

    success, error = give_card_to_user(user_id, username, chat_id)
    if success:
        players_db = load_data(PLAYERS_FILE)
        players_db[user_id]['last_godzik_time'] = datetime.now().isoformat()
        save_data(players_db, PLAYERS_FILE)
    else:
        bot.reply_to(message, error)

# ------------------ ДУЭЛЬ С КНОПКАМИ (ТОЛЬКО ДЛЯ ЦЕЛИ) ------------------
duel_invites = {}

@bot.message_handler(commands=['fight'])
def fight_command(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Пример: `/fight @ник`")
        return
    
    target_username = args[1].replace("@", "")
    challenger_id = message.from_user.id
    challenger_name = message.from_user.username or "Аноним"
    chat_id = message.chat.id
    
    players_db = load_data(PLAYERS_FILE)
    target_id = None
    for uid, data in players_db.items():
        if data.get('username') == target_username:
            target_id = uid
            break
            
    if not target_id:
        bot.reply_to(message, "❌ Игрок с таким никнеймом не найден в базе.")
        return
        
    if challenger_id == int(target_id):
        bot.reply_to(message, "❌ Нельзя вызвать самого себя на дуэль!")
        return

    invite_key = f"{chat_id}_{target_id}_{int(time.time())}"
    duel_invites[invite_key] = {
        'challenger_id': challenger_id,
        'challenger_name': challenger_name,
        'target_id': target_id,
        'target_username': target_username,
        'chat_id': chat_id
    }

    markup = types.InlineKeyboardMarkup()
    btn_accept = types.InlineKeyboardButton("⚔️ Принять", callback_data=f"duel_accept_{invite_key}")
    btn_decline = types.InlineKeyboardButton("❌ Отклонить", callback_data=f"duel_decline_{invite_key}")
    markup.add(btn_accept, btn_decline)

    bot.send_message(
        chat_id,
        f"⚔️ @{challenger_name} вызывает на дуэль @{target_username}!\n\n@{target_username}, прими вызов или откажись:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("duel_"))
def duel_callback(call):
    bot.answer_callback_query(call.id)
    data_parts = call.data.split('_')
    action = data_parts[1]
    invite_key = data_parts[2]
    
    if invite_key not in duel_invites:
        bot.send_message(call.message.chat.id, "❌ Приглашение устарело или уже было обработано.")
        return
        
    invite = duel_invites[invite_key]
    chat_id = invite['chat_id']
    
    if call.from_user.id != int(invite['target_id']):
        bot.send_message(call.message.chat.id, "❌ Только вызванный игрок может принять или отклонить дуэль.")
        return
        
    if action == "decline":
        bot.send_message(chat_id, f"❌ @{invite['target_username']} отклонил приглашение на дуэль.")
        del duel_invites[invite_key]
        return
        
    if action == "accept":
        bot.send_message(chat_id, f"⚔️ @{invite['target_username']} принял вызов! Бой начинается!")
        
        cards_db = load_data(DATA_FILE)
        if not cards_db:
            bot.send_message(chat_id, "❌ В колоде нет карт для дуэли!")
            del duel_invites[invite_key]
            return
            
        card_ids = list(cards_db.keys())
        if len(card_ids) < 2:
            bot.send_message(chat_id, "❌ В колоде недостаточно карт для дуэли (нужно минимум 2).")
            del duel_invites[invite_key]
            return

        card1_id = random.choice(card_ids)
        card2_id = random.choice([c for c in card_ids if c != card1_id])
        
        card1 = cards_db[card1_id]
        card2 = cards_db[card2_id]
        
        rarity_power = {
            "Редкая": 1,
            "Сверхредкая": 2,
            "Эпическая": 3,
            "Мифическая": 4,
            "Легендарка": 5
        }
        
        r1 = card1['rarity']
        r2 = card2['rarity']
        p1 = rarity_power.get(r1, 0)
        p2 = rarity_power.get(r2, 0)
        
        if p1 > p2:
            winner_id = invite['challenger_id']
            winner_name = invite['challenger_name']
            result_text = f"🏆 @{winner_name} ПОБЕДИЛ! Его карта **{card1['name']}** ({r1}) оказалась сильнее **{card2['name']}** ({r2})!\n💰 +20 монет!"
            players_db = load_data(PLAYERS_FILE)
            winner_id_str = str(winner_id)
            if winner_id_str in players_db:
                players_db[winner_id_str]['money'] += 20
                save_data(players_db, PLAYERS_FILE)
        elif p2 > p1:
            winner_id = invite['target_id']
            winner_name = invite['target_username']
            result_text = f"🏆 @{winner_name} ПОБЕДИЛ! Его карта **{card2['name']}** ({r2}) оказалась сильнее **{card1['name']}** ({r1})!\n💰 +20 монет!"
            players_db = load_data(PLAYERS_FILE)
            winner_id_str = str(winner_id)
            if winner_id_str in players_db:
                players_db[winner_id_str]['money'] += 20
                save_data(players_db, PLAYERS_FILE)
        else:
            result_text = f"🤝 Ничья! У обоих карты одинаковой редкости."
        
        bot.send_message(chat_id, result_text)
        del duel_invites[invite_key]

# ------------------ ЗАПУСК ------------------
if __name__ == "__main__":
    players_db = load_data(PLAYERS_FILE)
    bot_id_str = str(bot.get_me().id)
    if bot_id_str in players_db:
        del players_db[bot_id_str]
        save_data(players_db, PLAYERS_FILE)
        print(f"🧹 Бот удалён из базы игроков (ID: {bot_id_str})")

    print("🤖 Финальный стабильный бот полностью запущен!")
    bot.infinity_polling()