import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Загружаем токен
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Список валют
CURRENCIES = {
    'USD': {'name': 'Доллар', 'icon': '💵', 'id': 145},
    'EUR': {'name': 'Евро', 'icon': '💶', 'id': 19},
    'RUB': {'name': 'Российский рубль', 'icon': '₽', 'id': 298},
    'PLN': {'name': 'Злотый', 'icon': '💷', 'id': 195},
    'CNY': {'name': 'Юань', 'icon': '🇨🇳', 'id': 307},
}

# Хранилище данных пользователей
user_data = {}

# Функция получения курса валюты
def get_rate(currency_code):
    try:
        url = f"https://api.nbrb.by/exrates/rates/{currency_code}?parammode=2"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Ошибка API: {e}")
    return None

# Функция получения всех курсов
def get_all_rates():
    try:
        url = "https://api.nbrb.by/exrates/rates?periodicity=0"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Ошибка API: {e}")
    return None

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {'from': 'USD', 'to': 'RUB', 'amount': 1}
    
    keyboard = [
        [InlineKeyboardButton("💱 Конвертировать", callback_data='convert')],
        [InlineKeyboardButton("📊 Все курсы", callback_data='all_rates')],
        [InlineKeyboardButton("⚙️ Выбрать валюты", callback_data='choose_currencies')],
        [InlineKeyboardButton("ℹ️ О боте", callback_data='about')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔴 *MAJORIK CURRENCY BOT*\n"
        "Курсы Нацбанка Республики Беларусь\n\n"
        "Выбери действие:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# Обработка нажатий кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == 'convert':
        await show_converter(query, user_id)
    
    elif data == 'all_rates':
        await show_all_rates(query)
    
    elif data == 'choose_currencies':
        await choose_currencies(query, user_id)
    
    elif data == 'about':
        await query.edit_message_text(
            "🤖 *О боте*\n\n"
            "Версия: 2.0\n"
            "Источник: Нацбанк РБ (api.nbrb.by)\n"
            "Автор: @majorik\n\n"
            "Работает на python-telegram-bot + requests",
            parse_mode='Markdown'
        )
    
    elif data.startswith('set_from_'):
        currency = data.replace('set_from_', '')
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['from'] = currency
        await choose_currencies(query, user_id)
    
    elif data.startswith('set_to_'):
        currency = data.replace('set_to_', '')
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['to'] = currency
        await choose_currencies(query, user_id)
    
    elif data.startswith('amount_'):
        amount = int(data.replace('amount_', ''))
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['amount'] = amount
        await show_converter(query, user_id)

# Меню выбора валют
async def choose_currencies(query, user_id):
    if user_id not in user_data:
        user_data[user_id] = {'from': 'USD', 'to': 'RUB', 'amount': 1}
    
    from_curr = user_data[user_id].get('from', 'USD')
    to_curr = user_data[user_id].get('to', 'RUB')
    
    # Кнопки исходной валюты
    from_buttons = []
    for code, info in CURRENCIES.items():
        selected = "✅ " if code == from_curr else ""
        from_buttons.append([InlineKeyboardButton(
            f"{selected}{info['icon']} {code}",
            callback_data=f"set_from_{code}"
        )])
    
    # Кнопки целевой валюты
    to_buttons = []
    for code, info in CURRENCIES.items():
        selected = "✅ " if code == to_curr else ""
        to_buttons.append([InlineKeyboardButton(
            f"{selected}{info['icon']} {code}",
            callback_data=f"set_to_{code}"
        )])
    
    await query.edit_message_text(
        f"⚙️ *Настройка валют*\n\n"
        f"Сейчас: {from_curr} → {to_curr}\n\n"
        f"Выбери исходную валюту:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(from_buttons)
    )
    
    # Вторым сообщением отправляем выбор целевой валюты
    await query.message.reply_text(
        "Выбери целевую валюту:",
        reply_markup=InlineKeyboardMarkup(to_buttons)
    )

# Показать конвертер
async def show_converter(query, user_id):
    if user_id not in user_data:
        user_data[user_id] = {'from': 'USD', 'to': 'RUB', 'amount': 1}
    
    from_curr = user_data[user_id]['from']
    to_curr = user_data[user_id]['to']
    amount = user_data[user_id].get('amount', 1)
    
    # Кнопки выбора суммы
    amount_buttons = []
    amounts = [1, 10, 100, 500, 1000]
    for a in amounts:
        selected = "✅ " if a == amount else ""
        amount_buttons.append([InlineKeyboardButton(
            f"{selected}{a}",
            callback_data=f"amount_{a}"
        )])
    
    # Получаем курсы
    from_rate = get_rate(from_curr)
    to_rate = get_rate(to_curr)
    
    if not from_rate or not to_rate:
        await query.edit_message_text("❌ Ошибка получения курсов. Попробуй позже.")
        return
    
    # Конвертируем с учётом масштаба
    from_value = from_rate['Cur_OfficialRate'] / from_rate['Cur_Scale']
    to_value = to_rate['Cur_OfficialRate'] / to_rate['Cur_Scale']
    result = amount * from_value / to_value
    
    text = (
        f"💱 *Конвертер валют*\n\n"
        f"{amount} {from_curr} = *{result:.2f} {to_curr}*\n\n"
        f"📅 {datetime.now().strftime('%d.%m.%Y')}"
    )
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(amount_buttons)
    )

# Показать все курсы
async def show_all_rates(query):
    await query.edit_message_text("⏳ Загружаю курсы...")
    
    data = get_all_rates()
    
    if not data:
        await query.edit_message_text("❌ Ошибка загрузки курсов")
        return
    
    text = "📊 *Все курсы к BYN*\n\n"
    for curr in data[:15]:  # Покажем первые 15
        code = curr['Cur_Abbreviation']
        icon = CURRENCIES[code]['icon'] if code in CURRENCIES else '💱'
        
        rate = curr['Cur_OfficialRate']
        scale = curr['Cur_Scale']
        
        if scale > 1:
            text += f"{icon} {code}: {rate/scale:.4f} BYN (за {scale})\n"
        else:
            text += f"{icon} {code}: {rate:.4f} BYN\n"
    
    text += f"\n📅 {datetime.now().strftime('%d.%m.%Y')}"
    
    await query.edit_message_text(text, parse_mode='Markdown')

# Запуск бота
def main():
    print("🚀 Запуск бота...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Бот успешно запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()
