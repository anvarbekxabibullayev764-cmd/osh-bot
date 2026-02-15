import os
from flask import Flask, request
import telebot
from telebot import types

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN topilmadi!")

ADMIN_ID = 123456789  # <-- ADMIN ID
CARD_NUMBER = "9860080181652332"
OSH_PRICE = 25000

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

users = {}
orders = {}
shop_open = True

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
def start_handler(message):
    if not shop_open:
        bot.send_message(message.chat.id, "❌ Osh tugagan.")
        return

    users[message.chat.id] = {
        "step": "address"
    }

    bot.send_message(message.chat.id, "🏠 To‘liq manzil yozing:")

# ================= CONTACT =================

@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    user = users.get(message.chat.id)
    if not user:
        return

    user["phone"] = message.contact.phone_number
    user["step"] = "portion"

    bot.send_message(message.chat.id, "⚖️ Necha porsiya osh olasiz?")

# ================= PHOTO =================

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    user = users.get(message.chat.id)
    if not user or user.get("step") != "check":
        return

    bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption="💳 To‘lov cheki"
    )

    confirm_order(message)

# ================= TEXT HANDLER =================

@bot.message_handler(content_types=['text'])
def text_handler(message):
    user = users.get(message.chat.id)
    if not user:
        return

    step = user.get("step")

    # 1️⃣ ADDRESS
    if step == "address":
        user["address"] = message.text
        user["step"] = "phone"

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("📱 Telefon yuborish", request_contact=True))

        bot.send_message(
            message.chat.id,
            "📞 Telefon raqamingizni yuboring:",
            reply_markup=kb
        )
        return

    # 2️⃣ PORTION
    if step == "portion":
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❗ Faqat son kiriting.")
            return

        user["portion"] = int(message.text)
        total = user["portion"] * OSH_PRICE
        user["total"] = total
        user["step"] = "payment"

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("💵 Naqd", "💳 Karta")

        bot.send_message(
            message.chat.id,
            f"💰 Jami: <b>{total}</b> so'm\nTo‘lov turini tanlang:",
            reply_markup=kb
        )
        return

    # 3️⃣ PAYMENT
    if step == "payment":
        if message.text not in ["💵 Naqd", "💳 Karta"]:
            bot.send_message(message.chat.id, "To‘lov turini tanlang.")
            return

        user["payment"] = message.text

        if message.text == "💳 Karta":
            user["step"] = "check"
            bot.send_message(
                message.chat.id,
                f"💳 To‘lov kartasi:\n<b>{CARD_NUMBER}</b>\n\nChek rasmini yuboring."
            )
        else:
            confirm_order(message)

        return

# ================= CONFIRM ORDER =================

def confirm_order(message):
    user = users.get(message.chat.id)
    if not user:
        return

    order_id = len(orders) + 1

    orders[order_id] = {
        "user_id": message.chat.id,
        "data": user
    }

    text = (
        f"🆕 <b>Zakaz #{order_id}</b>\n\n"
        f"👤 ID: {message.chat.id}\n"
        f"📍 Manzil: {user['address']}\n"
        f"📞 Tel: {user.get('phone')}\n"
        f"🍽 Porsiya: {user['portion']}\n"
        f"💰 Jami: {user['total']} so'm\n"
        f"💳 To‘lov: {user['payment']}"
    )

    bot.send_message(ADMIN_ID, text)

    bot.send_message(
        message.chat.id,
        "✅ Zakazingiz qabul qilindi.\nTez orada yetkazib beramiz 🚚",
        reply_markup=types.ReplyKeyboardRemove()
    )

    users.pop(message.chat.id)

# ================= SERVER =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
