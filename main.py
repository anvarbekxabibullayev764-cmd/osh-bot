import os
from flask import Flask, request
import telebot
from telebot import types

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN topilmadi! Render Environment ga qo‘shing.")

ADMIN_ID = 123456789  # <-- O'Z ID INGIZNI YOZING
CARD_NUMBER = "9860080181652332"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

users = {}
orders = {}
couriers = {}
stats = {}

shop_open = True
osh_price = 25000

# ================= WEBHOOK =================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Bot ishlayapti 🚀", 200

# ================= START =================

@bot.message_handler(commands=['start'])
def start(message):
    if not shop_open:
        bot.send_message(message.chat.id, "❌ Osh tugagan.")
        return

    users[message.chat.id] = {}

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📱 Telefon yuborish", request_contact=True))

    bot.send_message(message.chat.id, "🏠 To‘liq manzil yozing:")
    bot.send_message(message.chat.id, "📞 Telefon raqamingizni yuboring:", reply_markup=kb)

# ================= CONTACT =================

@bot.message_handler(content_types=['contact'])
def contact(message):
    if message.chat.id not in users:
        return
    users[message.chat.id]["phone"] = message.contact.phone_number
    bot.send_message(message.chat.id, "⚖️ Necha porsiya osh?")

# ================= TEXT HANDLER =================

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.chat.id not in users:
        return

    user = users[message.chat.id]

    # Address
    if "address" not in user:
        user["address"] = message.text
        return

    # Portion
    if "portion" not in user:
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "Faqat son kiriting.")
            return

        user["portion"] = int(message.text)
        total = user["portion"] * osh_price

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("💵 Naqd", "💳 Karta")

        bot.send_message(
            message.chat.id,
            f"💰 Jami: {total} so'm\nTo‘lov turini tanlang:",
            reply_markup=kb
        )
        return

    # Payment
    if message.text in ["💵 Naqd", "💳 Karta"]:
        user["payment"] = message.text

        if message.text == "💳 Karta":
            bot.send_message(
                message.chat.id,
                f"💳 To‘lov kartasi:\n{CARD_NUMBER}\n\nChek rasmini yuboring."
            )
            return
        else:
            confirm_order(message)
            return

# ================= PHOTO =================

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    if message.chat.id not in users:
        return

    bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption="💳 To‘lov cheki"
    )

    confirm_order(message)

# ================= CONFIRM =================

def confirm_order(message):
    order_id = len(orders) + 1
    data = users[message.chat.id]

    orders[order_id] = {
        "user": message.chat.id,
        "data": data,
        "status": "new"
    }

    bot.send_message(
        ADMIN_ID,
        f"🆕 Zakaz #{order_id}\n\n{data}"
    )

    bot.send_message(message.chat.id, "✅ Zakazingiz qabul qilindi.")
    users.pop(message.chat.id)

# ================= SERVER =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
