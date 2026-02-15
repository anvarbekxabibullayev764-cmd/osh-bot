import telebot
from telebot import types
import os
import re
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

user_data = {}

# START
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

# CONTACT orqali raqam
@bot.message_handler(content_types=['contact'])
def get_contact(message):
    phone = message.contact.phone_number
    user_data[message.chat.id]["phone"] = phone

    bot.send_message(
        message.chat.id,
        "🏠 Manzilingizni yozing:"
    )

# Oddiy yozilgan raqam
@bot.message_handler(func=lambda message: message.text and re.match(r"^\+998\d{9}$", message.text))
def get_phone_text(message):
    user_data.setdefault(message.chat.id, {})
    user_data[message.chat.id]["phone"] = message.text

    bot.send_message(
        message.chat.id,
        "🏠 Manzilingizni yozing:"
    )

# Manzil
@bot.message_handler(func=lambda message: message.chat.id in user_data and "phone" in user_data[message.chat.id] and "address" not in user_data[message.chat.id])
def get_address(message):
    user_data[message.chat.id]["address"] = message.text

    bot.send_message(
        message.chat.id,
        "⚖️ Buyurtma vaznini kiriting (kg da):"
    )

# Vazn
@bot.message_handler(func=lambda message: message.chat.id in user_data and "address" in user_data[message.chat.id] and "weight" not in user_data[message.chat.id])
def get_weight(message):
    if not message.text.replace(".", "").isdigit():
        bot.send_message(message.chat.id, "❌ Iltimos faqat raqam kiriting (masalan: 2 yoki 1.5)")
        return

    user_data[message.chat.id]["weight"] = message.text

    data = user_data[message.chat.id]

    summary = (
        f"📦 <b>Buyurtma ma'lumotlari:</b>\n\n"
        f"📞 Telefon: {data['phone']}\n"
        f"🏠 Manzil: {data['address']}\n"
        f"⚖️ Vazn: {data['weight']} kg\n\n"
        f"✅ Tasdiqlaysizmi?"
    )

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("✅ Ha", "❌ Yo‘q")

    bot.send_message(message.chat.id, summary, reply_markup=keyboard)

# Tasdiqlash
@bot.message_handler(func=lambda message: message.text in ["✅ Ha", "❌ Yo‘q"])
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
        f"📞 Telefon: {data['phone']}\n"
        f"🏠 Manzil: {data['address']}\n"
        f"⚖️ Vazn: {data['weight']} kg"
    )

    # Admin ga yuborish
    if ADMIN_ID:
        bot.send_message(ADMIN_ID, order_text)

    bot.send_message(message.chat.id, "✅ Buyurtmangiz qabul qilindi! Tez orada bog‘lanamiz.")

    user_data.pop(message.chat.id, None)

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
