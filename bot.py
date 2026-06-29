import telebot
from telebot import types
from datetime import datetime
import json
import os
import requests

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = '8575996468:AAFAURwiyXTnnb76L-4UsMULmHbRknIDdeY'
ADMIN_FILE = 'admins.json'
LEADS_FILE = 'leads.json'

# Supabase настройки
SUPABASE_URL = 'https://osgqobfvmdaxuhutqcjq.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zZ3FvYmZ2bWRheHVodXRxY2pxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI3NjIwNDgsImV4cCI6MjA5ODMzODA0OH0.nyl3RKAfifM3jkkJlIj2webmkuHHfBtJHrixdumpXmY'

def save_lead_to_supabase(lead):
    """Отправляет лид в Supabase"""
    try:
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
        response = requests.post(
            f'{SUPABASE_URL}/rest/v1/leads',
            json=lead,
            headers=headers,
            timeout=5
        )
        if response.status_code in [200, 201]:
            print(f"✅ Лид отправлен в Supabase")
        else:
            print(f"❌ Ошибка Supabase: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Ошибка сети Supabase: {e}")

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# ==================== РАБОТА С ФАЙЛАМИ ====================
def load_admins():
    if os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_admins(admins):
    with open(ADMIN_FILE, 'w', encoding='utf-8') as f:
        json.dump(admins, f, ensure_ascii=False, indent=2)

def load_leads():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_leads(leads):
    with open(LEADS_FILE, 'w', encoding='utf-8') as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

def add_admin(admin_id):
    admins = load_admins()
    if admin_id not in admins:
        admins.append(admin_id)
        save_admins(admins)
        return True
    return False

def remove_admin(admin_id):
    admins = load_admins()
    if admin_id in admins:
        admins.remove(admin_id)
        save_admins(admins)
        return True
    return False

def is_admin(user_id):
    return user_id in load_admins()

# ==================== ХРАНИЛИЩЕ СОСТОЯНИЙ ====================
user_states = {}

# ==================== КЛАВИАТУРЫ ====================
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('🏠 ВНЖ / Визы'),
        types.KeyboardButton(' Паспорт / Гражданство')
    )
    markup.add(
        types.KeyboardButton(' Роды за рубежом'),
        types.KeyboardButton('💼 Другое')
    )
    return markup

def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(" Статистика", callback_data='admin_stats'),
        types.InlineKeyboardButton("📋 Лиды", callback_data='admin_leads')
    )
    markup.add(
        types.InlineKeyboardButton("➕ Выдать админку", callback_data='admin_add'),
        types.InlineKeyboardButton("➖ Забрать админку", callback_data='admin_remove')
    )
    return markup

def back_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(" Назад", callback_data='admin_back'))
    return markup

# ==================== КОМАНДЫ ====================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    args = message.text.split()
    
    if is_admin(chat_id):
        bot.send_message(
            chat_id,
            "🔧 *Админ-панель*\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=admin_keyboard()
        )
        return
    
    user_states[chat_id] = {'step': 'start'}
    
    if len(args) > 1:
        param = args[1]
        if param.startswith('consultation_'):
            source = param.replace('consultation_', '')
            user_states[chat_id]['source'] = source
        elif param.startswith('program_'):
            program_id = param.replace('program_', '')
            user_states[chat_id]['program'] = program_id
            user_states[chat_id]['source'] = f'program_{program_id}'
            user_states[chat_id]['step'] = 'program_selected'
    
    bot.send_message(
        chat_id,
        "👋 *Привет! Это бот агентства Relocate.*\n\n"
        "Мы помогаем с:\n"
        "• ВНЖ и визами\n"
        "• Паспортами и гражданством\n"
        "• Родами за рубежом\n\n"
        "Выберите категорию вопроса:",
        parse_mode='Markdown',
        reply_markup=main_keyboard()
    )

@bot.message_handler(commands=['admin'])
def admin_command(message):
    chat_id = message.chat.id
    if not is_admin(chat_id):
        return
    bot.send_message(
        chat_id,
        "🔧 *Админ-панель*\n\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=admin_keyboard()
    )

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    
    if not is_admin(chat_id):
        bot.answer_callback_query(call.id, " Доступ запрещён", show_alert=True)
        return
    
    if call.data == 'admin_stats':
        leads = load_leads()
        total = len(leads)
        hot = len([l for l in leads if l.get('status') == 'hot'])
        warm = len([l for l in leads if l.get('status') == 'warm'])
        cold = len([l for l in leads if l.get('status') == 'cold'])
        converted = len([l for l in leads if l.get('status') == 'converted'])
        
        stats_text = (
            f"📊 *Статистика за сегодня:*\n\n"
            f"Всего лидов: {total}\n"
            f"🔥 Горячих: {hot}\n"
            f"🟡 Тёплых: {warm}\n"
            f"⚪ Холодных: {cold}\n"
            f"✅ Конверсий: {converted}"
        )
        bot.send_message(chat_id, stats_text, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    
    elif call.data == 'admin_leads':
        leads = load_leads()
        if not leads:
            bot.send_message(chat_id, " Пока нет лидов")
        else:
            for lead in leads[-10:]:
                msg = (
                    f"🔥 *НОВЫЙ ЛИД*\n\n"
                    f"👤 Пользователь: {lead.get('username', 'Не указан')}\n"
                    f"📞 Контакт: {lead.get('contact', 'Не указан')}\n"
                    f" Категория: {lead.get('category', 'Не указана')}\n"
                    f"🎯 Программа: {lead.get('program', 'Не указана')}\n"
                    f"📍 Источник: {lead.get('source', 'Прямой переход')}\n"
                    f"⏰ Время: {lead.get('time', 'Не указано')}\n"
                    f"⭐ Статус: {lead.get('status', 'new')}"
                )
                bot.send_message(chat_id, msg, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    
    elif call.data == 'admin_add':
        msg = bot.send_message(
            chat_id,
            "➕ *Добавить админа*\n\n"
            "Отправьте Telegram ID нового админа:\n"
            "(узнать ID можно через @userinfobot)",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        bot.register_next_step_handler(msg, handle_add_admin)
        bot.answer_callback_query(call.id)
    
    elif call.data == 'admin_remove':
        admins = load_admins()
        if not admins:
            bot.send_message(chat_id, "📭 Нет активных админов")
            bot.answer_callback_query(call.id)
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for admin_id in admins:
            markup.add(types.InlineKeyboardButton(
                f"👤 {admin_id}",
                callback_data=f'remove_{admin_id}'
            ))
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data='admin_back'))
        
        bot.send_message(
            chat_id,
            "➖ *Забрать админку*\n\n"
            "Выберите админа, у которого хотите забрать права:",
            parse_mode='Markdown',
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith('remove_'):
        admin_id_to_remove = int(call.data.replace('remove_', ''))
        if remove_admin(admin_id_to_remove):
            bot.send_message(
                chat_id,
                f"✅ Админка забрана у {admin_id_to_remove}",
                reply_markup=admin_keyboard()
            )
            try:
                bot.send_message(
                    admin_id_to_remove,
                    "️ У вас забрали права администратора в боте Relocate Agency"
                )
            except:
                pass
        else:
            bot.send_message(chat_id, "❌ Ошибка при удалении админа")
        bot.answer_callback_query(call.id)
    
    elif call.data == 'admin_back':
        bot.send_message(
            chat_id,
            "🔧 *Админ-панель*\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=admin_keyboard()
        )
        bot.answer_callback_query(call.id)

# ==================== ОБРАБОТКА ДОБАВЛЕНИЯ АДМИНА ====================
def handle_add_admin(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    if text == ' Назад':
        bot.send_message(
            chat_id,
            "🔧 *Админ-панель*",
            parse_mode='Markdown',
            reply_markup=admin_keyboard()
        )
        return
    
    try:
        new_admin_id = int(text)
        if add_admin(new_admin_id):
            bot.send_message(
                chat_id,
                f"✅ Админ {new_admin_id} успешно добавлен!",
                reply_markup=admin_keyboard()
            )
            try:
                bot.send_message(
                    new_admin_id,
                    "🎉 *Вас добавили в админы!*\n\n"
                    "Теперь вы можете управлять ботом Relocate Agency.\n"
                    "Используйте команду /admin для доступа к панели.",
                    parse_mode='Markdown'
                )
            except:
                pass
        else:
            bot.send_message(chat_id, "⚠️ Этот пользователь уже админ")
    except ValueError:
        bot.send_message(chat_id, "❌ Ошибка! Отправьте числовой ID")

# ==================== ОБРАБОТКА СООБЩЕНИЙ ПОЛЬЗОВАТЕЛЕЙ ====================
@bot.message_handler(content_types=['text'])
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    if is_admin(chat_id):
        return
    
    if chat_id not in user_states:
        user_states[chat_id] = {'step': 'start'}
    
    state = user_states[chat_id]
    
    if text == '❌ Отмена':
        bot.send_message(
            chat_id,
            "Хорошо. Если будут вопросы — пишите!",
            reply_markup=types.ReplyKeyboardRemove()
        )
        if chat_id in user_states:
            del user_states[chat_id]
        return
    
    if state.get('step') in ['start', 'category']:
        category_map = {
            ' ВНЖ / Визы': 'ВНЖ / Визы',
            '🛂 Паспорт / Гражданство': 'Паспорт / Гражданство',
            '👶 Роды за рубежом': 'Роды за рубежом',
            '💼 Другое': 'Другое'
        }
        
        if text in category_map:
            state['category'] = category_map[text]
            state['step'] = 'contact'
            
            bot.send_message(
                chat_id,
                f"✅ Отлично! Вы выбрали: *{state['category']}*\n\n"
                f"Оставьте ваш *@username телеграм* и *номер телефона*. "
                f"Менеджер с вами очень скоро свяжется!🤗",
                parse_mode='Markdown'
            )
        else:
            bot.send_message(
                chat_id,
                "Пожалуйста, выберите категорию из меню:",
                reply_markup=main_keyboard()
            )
        return
    
    if state.get('step') == 'contact':
        username = f"@{message.from_user.username}" if message.from_user.username else "Не указан"
        
        lead = {
            'id': len(load_leads()) + 1,
            'date': datetime.now().strftime('%d.%m.%Y'),
            'time': datetime.now().strftime('%H:%M'),
            'username': username,
            'contact': text,
            'category': state.get('category', 'Не указана'),
            'program': state.get('program', 'Не указана'),
            'source': state.get('source', 'Прямой переход'),
            'status': 'hot',
            'commission': '€200'
        }
        
        # Сохраняем локально
        leads = load_leads()
        leads.append(lead)
        save_leads(leads)
        
        # === ОТПРАВКА В SUPABASE ===
        save_lead_to_supabase(lead)
        # ===================================
        
        # Уведомление админам
        admins = load_admins()
        notification = (
            f"🔥 *НОВЫЙ ЛИД #{lead['id']}*\n\n"
            f"👤 Пользователь: {lead['username']}\n"
            f" Контакт: {text}\n"
            f"📂 Категория: {lead['category']}\n"
            f"🎯 Программа: {lead['program']}\n"
            f" Источник: {lead['source']}\n"
            f"⏰ Время: {lead['time']}\n"
            f"⭐ Статус: 🔥 Горячий"
        )
        
        for admin_id in admins:
            try:
                bot.send_message(admin_id, notification, parse_mode='Markdown')
            except:
                pass
        
        bot.send_message(
            chat_id,
            "✅ *Спасибо!* Наш менеджер свяжется с вами в ближайшее время.\n\n"
            "Если у вас есть срочные вопросы, напишите нам напрямую.",
            parse_mode='Markdown'
        )
        
        if chat_id in user_states:
            del user_states[chat_id]
        return
    
    bot.send_message(
        chat_id,
        "👋 Здравствуйте! Выберите категорию вопроса:",
        reply_markup=main_keyboard()
    )

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    if not os.path.exists(ADMIN_FILE):
        save_admins([])
    if not os.path.exists(LEADS_FILE):
        save_leads([])
    
    print("🤖 Бот запущен...")
    print(f" Файл админов: {ADMIN_FILE}")
    print(f"📁 Файл лидов: {LEADS_FILE}")
    bot.polling(none_stop=True, interval=0)
