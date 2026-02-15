import os
import json
import logging
from datetime import datetime
from threading import Thread
from flask import Flask
import telebot

# ================== CONFIG ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

if not ADMIN_ID:
    raise ValueError("ADMIN_ID topilmadi!")

ADMIN_ID = int(ADMIN_ID)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DATA_FILE = "data.json"

# ================== LOGGING ==================

logging.basicConfig(level=logging.INFO)

# ================== DATABASE ==================

def init_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"orders": [], "stop": False}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

init_data()

# ================== BOT HANDLERS ==================

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.send_message(
        message.chat.id,
        "👋 Assalomu alaykum!\n\n📞 Telefon raqamingizni yuboring.",
    )

@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    data = load_data()

    if data["stop"]:
        bot.send_message(message.chat.id, "🚫 Hozir buyurtma qabul qilinmaydi.")
        return

    phone = message.contact.phone_number
    msg = bot.send_message(message.chat.id, "🏠 Manzilingizni yozing:")
    bot.register_next_step_handler(msg, address_handler, phone)

def address_handler(message, phone):
    address = message.text

    order = {
        "user_id": message.chat.id,
        "phone": phone,
        "address": address,
        "status": "pending",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    data = load_data()
    data["orders"].append(order)
    save_data(data)

    bot.send_message(message.chat.id, "✅ Buyurtmangiz qabul qilindi!")

    bot.send_message(
        ADMIN_ID,
        f"🆕 <b>Yangi buyurtma</b>\n\n"
        f"📞 Telefon: {phone}\n"
        f"🏠 Manzil: {address}"
    )

# ================== ADMIN COMMANDS ==================

@bot.message_handler(commands=['stop'])
def stop_orders(message):
    if message.chat.id == ADMIN_ID:
        data = load_data()
        data["stop"] = True
        save_data(data)
        bot.send_message(message.chat.id, "⛔ Buyurtmalar to‘xtatildi.")

@bot.message_handler(commands=['start_orders'])
def start_orders(message):
    if message.chat.id == ADMIN_ID:
        data = load_data()
        data["stop"] = False
        save_data(data)
        bot.send_message(message.chat.id, "✅ Buyurtmalar yoqildi.")

# ================== FLASK (RENDER UCHUN) ==================

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running successfully!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ================== START ==================

if __name__ == "__main__":
    Thread(target=run_web).start()
    logging.info("Bot ishga tushdi...")
    bot.infinity_polling()
