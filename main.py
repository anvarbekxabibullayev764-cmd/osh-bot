import telebot
from telebot import types
import os
from datetime import datetime

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN topilmadi!")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

ADMIN_ID = 5915034478
ADMIN_NAME = "ANVARBEK"

COURIERS = {
    589856755: "Javohir",
    710708974: "Hazratillo"
}

PRICE_PER_KG = 40000
SALAT_PRICE = 5000

# ================= GLOBAL STATE =================
osh_active = True
user_data = {}
orders = {}
order_counter = 0
total_orders = 0
total_income = 0
ratings = []

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    if not osh_active:
        bot.send_message(message.chat.id, "❌ Hozir osh sotuvda emas.")
        return

    bot.send_message(
        message.chat.id,
        "🍚 Necha kg osh?\n1 KG = 40 000 so'm"
    )

# ================= ADMIN PANEL =================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_ID:
        return

    avg = round(sum(ratings)/len(ratings), 1) if ratings else 0

    text = f"""
👑 <b>ADMIN PANEL ({ADMIN_NAME})</b>

🍚 Holat: {"🟢 Ochiq" if osh_active else "🔴 Yopiq"}
📦 Jami zakaz: {total_orders}
💰 Umumiy daromad: {total_income:,} so'm
⭐ O'rtacha reyting: {avg}

Buyruqlar:
/start_osh
/stop_osh
/stat
"""
    bot.send_message(ADMIN_ID, text)

# ================= START OSH =================
@bot.message_handler(commands=['start_osh'])
def start_osh(message):
    global osh_active
    if message.chat.id == ADMIN_ID:
        osh_active = True
        bot.send_message(ADMIN_ID, "🟢 Osh sotuvga ochildi")

# ================= STOP OSH =================
@bot.message_handler(commands=['stop_osh'])
def stop_osh(message):
    global osh_active
    if message.chat.id == ADMIN_ID:
        osh_active = False
        bot.send_message(ADMIN_ID, "🔴 Osh yopildi")

# ================= STAT =================
@bot.message_handler(commands=['stat'])
def stat(message):
    if message.chat.id != ADMIN_ID:
        return

    avg = round(sum(ratings)/len(ratings), 1) if ratings else 0

    bot.send_message(
        ADMIN_ID,
        f"""
📊 <b>STATISTIKA</b>

📦 Zakazlar: {total_orders}
💰 Daromad: {total_income:,} so'm
⭐ Reytinglar soni: {len(ratings)}
⭐ O'rtacha: {avg}
"""
    )

# ================= KG =================
@bot.message_handler(func=lambda m: m.text and m.text.isdigit())
def get_kg(message):
    if not osh_active:
        return

    user_data[message.chat.id] = {"kg": float(message.text)}
    bot.send_message(message.chat.id, "🥗 Salat olasizmi? (Ha/Yo'q)")

# ================= SALAT =================
@bot.message_handler(func=lambda m: m.text and m.text.lower() in ["ha", "yo'q"])
def get_salat(message):
    if message.chat.id not in user_data:
        return

    user_data[message.chat.id]["salat"] = message.text
    bot.send_message(message.chat.id, "💳 To'lov turi? (Naqd/Karta)")

# ================= PAYMENT =================
@bot.message_handler(func=lambda m: m.text and m.text.lower() in ["naqd", "karta"])
def get_payment(message):
    global order_counter, total_orders, total_income

    if message.chat.id not in user_data:
        return

    if "kg" not in user_data[message.chat.id] or "salat" not in user_data[message.chat.id]:
        return

    kg = user_data[message.chat.id]["kg"]
    salat = user_data[message.chat.id]["salat"]
    payment = message.text

    total = kg * PRICE_PER_KG
    if salat.lower() == "ha":
        total += SALAT_PRICE

    order_counter += 1
    total_orders += 1
    total_income += total
    order_id = order_counter

    orders[order_id] = {
        "taken": False,
        "courier": None
    }

    text = f"""
🆕 <b>BUYURTMA #{order_id}</b>

👤 {message.from_user.first_name}
🆔 {message.from_user.id}
🍚 Kg: {kg}
🥗 Salat: {salat}
💳 To'lov: {payment}
💰 {total:,} so'm
🕒 {datetime.now().strftime('%H:%M')}
"""

    bot.send_message(
        message.chat.id,
        f"✅ Zakaz qabul qilindi!\nBuyurtma: #{order_id}\n\n⭐ Reyting bering (1-5)"
    )

    bot.send_message(ADMIN_ID, text)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "✅ Qabul qilish",
        callback_data=f"take_{order_id}"
    ))

    for courier_id in COURIERS:
        bot.send_message(courier_id, text, reply_markup=markup)

# ================= COURIER TAKE =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("take_"))
def take_order(call):
    try:
        order_id = int(call.data.split("_")[1])

        if call.from_user.id not in COURIERS:
            return

        if order_id not in orders:
            return

        if orders[order_id]["taken"]:
            bot.answer_callback_query(call.id, "❌ Bu zakaz olingan")
            return

        orders[order_id]["taken"] = True
        courier_name = COURIERS[call.from_user.id]
        orders[order_id]["courier"] = courier_name

        # Tugmani hamma kuriyerda o‘chirish
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )

        bot.send_message(
            call.message.chat.id,
            f"🚴 Zakazni {courier_name} qabul qildi"
        )

        bot.send_message(
            ADMIN_ID,
            f"📦 #{order_id} zakazni {courier_name} oldi"
        )

    except Exception as e:
        print("Callback error:", e)

# ================= RATING =================
@bot.message_handler(func=lambda m: m.text in ["1", "2", "3", "4", "5"])
def rating(message):
    ratings.append(int(message.text))
    bot.send_message(message.chat.id, "⭐ Rahmat! Bahoyingiz qabul qilindi.")

# ================= SAFE POLLING =================
print("🚀 Bot ishga tushdi...")

bot.infinity_polling(
    skip_pending=True,
    timeout=60,
    long_polling_timeout=60
)
