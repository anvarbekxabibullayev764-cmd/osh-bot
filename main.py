import telebot
from telebot import types
import os
import json
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "data.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({
            "price": 25000,
            "stop": False,
            "couriers": {},
            "orders": []
        }, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@bot.message_handler(commands=['start'])
def start(message):
    data = load_data()
    if data["stop"]:
        bot.send_message(message.chat.id, "❌ Bugun osh tugagan.")
        return

    bot.send_message(message.chat.id,
                     f"🍚 Osh narxi: {data['price']} so'm\nTelefon raqamingizni yuboring.",
                     reply_markup=phone_markup())

def phone_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton("📞 Telefon yuborish", request_contact=True)
    markup.add(button)
    return markup

@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    phone = message.contact.phone_number
    bot.send_message(message.chat.id, "🏠 Uy raqamingizni yozing.")
    bot.register_next_step_handler(message, address_handler, phone)

def address_handler(message, phone):
    address = message.text
    data = load_data()

    order = {
        "user_id": message.chat.id,
        "phone": phone,
        "address": address,
        "status": "pending",
        "time": str(datetime.now())
    }

    data["orders"].append(order)
    save_data(data)

    bot.send_message(message.chat.id, "✅ Zakaz qabul qilindi.")

    bot.send_message(ADMIN_ID,
                     f"🆕 Yangi zakaz\nTelefon: {phone}\nManzil: {address}")

@bot.message_handler(commands=['stop'])
def stop_orders(message):
    if message.chat.id == ADMIN_ID:
        data = load_data()
        data["stop"] = True
        save_data(data)
        bot.send_message(message.chat.id, "⛔ Zakazlar to'xtatildi.")

@bot.message_handler(commands=['start_orders'])
def start_orders(message):
    if message.chat.id == ADMIN_ID:
        data = load_data()
        data["stop"] = False
        save_data(data)
        bot.send_message(message.chat.id, "✅ Zakazlar yoqildi.")

bot.polling()
