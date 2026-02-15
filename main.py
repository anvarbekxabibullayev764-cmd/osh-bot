import os
import telebot
from telebot import types
from flask import Flask, request
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ===== WEBHOOK ROUTE =====
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# ===== HEALTH CHECK =====
@app.route("/", methods=["GET"])
def index():
    return "Bot ishlayapti 🚀", 200

# ===== BOT LOGIC =====
user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    contact_btn = types.KeyboardButton("📱 Raqamni yuborish", request_contact=True)
    keyboard.add(contact_btn)

    user_data[message.chat.id] = {}

    bot.send_message(
        message.chat.id,
        "👋 <b>Assalomu alaykum!</b>\n\n📞 Telefon raqamingizni yuboring.",
        reply_markup=keyboard
    )

@bot.message_handler(content_types=['contact'])
def get_contact(message):
    user_data.setdefault(message.chat.id, {})
    user_data[message.chat.id]["phone"] = message.contact.phone_number
    bot.send_message(message.chat.id, "🏠 Manzilingizni yozing:")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("+998") and len(m.text) == 13)
def get_phone_text(message):
    user_data.setdefault(message.chat.id, {})
    user_data[message.chat.id]["phone"] = message.text
    bot.send_message(message.chat.id, "🏠 Manzilingizni yozing:")

@bot.message_handler(func=lambda m: m.chat.id in user_data and "phone" in user_data[m.chat.id] and "address" not in user_data[m.chat.id])
def get_address(message):
    user_data[message.chat.id]["address"] = message.text
    bot.send_message(message.chat.id, "⚖️ Buyurtma vaznini kiriting (kg):")

@bot.message_handler(func=lambda m: m.chat.id in user_data and "address" in user_data[m.chat.id] and "weight" not in user_data[m.chat.id])
def get_weight(message):
    if not message.text.replace(".", "").isdigit():
        bot.send_message(message.chat.id, "❌ Faqat raqam kiriting (masalan 1 yoki 1.5)")
        return

    user_data[message.chat.id]["weight"] = message.text
    data = user_data[message.chat.id]

    summary = (
        f"📦 <b>Buyurtma:</b>\n\n"
        f"📞 {data['phone']}\n"
        f"🏠 {data['address']}\n"
        f"⚖️ {data['weight']} kg\n\n"
        f"✅ Tasdiqlaysizmi?"
    )

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("✅ Ha", "❌ Yo‘q")

    bot.send_message(message.chat.id, summary, reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text in ["✅ Ha", "❌ Yo‘q"])
def confirm(message):
    if message.text == "❌ Yo‘q":
        user_data.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Bekor qilindi. /start ni bosing.")
        return

    data = user_data.get(message.chat.id)
    if not data:
        bot.send_message(message.chat.id, "Xatolik. /start ni bosing.")
        return

    order_text = (
        f"🆕 <b>Yangi buyurtma!</b>\n\n"
        f"👤 ID: {message.chat.id}\n"
        f"📞 {data['phone']}\n"
        f"🏠 {data['address']}\n"
        f"⚖️ {data['weight']} kg"
    )

    bot.send_message(message.chat.id, "✅ Buyurtmangiz qabul qilindi!")
    user_data.pop(message.chat.id, None)

# ===== START SERVER =====
if __name__ == "__main__":
    bot.remove_webhook()
    RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
    if not RENDER_URL:
        raise ValueError("RENDER_EXTERNAL_URL topilmadi!")

    bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
