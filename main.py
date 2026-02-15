import os
from flask import Flask, request
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 123456789  # <-- BU YERGA O'Z ID INGIZNI YOZING

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
    return "Professional Bot ishlayapti 🚀", 200


# ================= START =================

@bot.message_handler(commands=['start'])
def start(message):
    if not shop_open:
        bot.send_message(message.chat.id, "❌ Kech qoldingiz, osh tugagan.")
        return

    users[message.chat.id] = {}

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📱 Telefon yuborish", request_contact=True))

    bot.send_message(
        message.chat.id,
        "🏠 To‘liq manzil yozing.\n\nMasalan:\nGulobod 1-don 4-padez\n\n⚠️ Faqat padezgacha yetkaziladi.",
    )

    bot.send_message(message.chat.id, "📞 Telefon raqamingizni yuboring:", reply_markup=kb)


# ================= CONTACT =================

@bot.message_handler(content_types=['contact'])
def contact(message):
    users[message.chat.id]["phone"] = message.contact.phone_number
    bot.send_message(message.chat.id, "⚖️ Necha porsiya osh?")


# ================= ADDRESS =================

@bot.message_handler(func=lambda m: m.chat.id in users and "address" not in users[m.chat.id])
def address(message):
    users[message.chat.id]["address"] = message.text


# ================= PORTION =================

@bot.message_handler(func=lambda m: m.chat.id in users and "phone" in users[m.chat.id] and "portion" not in users[m.chat.id])
def portion(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "Faqat son kiriting.")
        return

    users[message.chat.id]["portion"] = int(message.text)
    total = users[message.chat.id]["portion"] * osh_price

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💵 Naqd", "💳 Karta")

    bot.send_message(
        message.chat.id,
        f"💰 Jami: {total} so'm\n\nTo‘lov turini tanlang:",
        reply_markup=kb
    )


# ================= PAYMENT =================

@bot.message_handler(func=lambda m: m.text in ["💵 Naqd", "💳 Karta"])
def payment(message):
    users[message.chat.id]["payment"] = message.text

    if message.text == "💳 Karta":
        bot.send_message(
            message.chat.id,
            f"💳 To‘lov kartasi:\n{CARD_NUMBER}\n\nTo‘lovdan keyin chek rasmini yuboring."
        )
    else:
        confirm_order(message)


# ================= CHEK =================

@bot.message_handler(content_types=['photo'])
def check_photo(message):
    if message.chat.id not in users:
        return

    bot.send_photo(ADMIN_ID, message.photo[-1].file_id,
                   caption="💳 Karta orqali to‘lov cheki")
    confirm_order(message)


# ================= CONFIRM ORDER =================

def confirm_order(message):
    order_id = len(orders) + 1
    data = users[message.chat.id]

    orders[order_id] = {
        "user": message.chat.id,
        "data": data,
        "status": "new"
    }

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🚚 Zakazni olish", callback_data=f"take_{order_id}"))

    bot.send_message(
        ADMIN_ID,
        f"🆕 Zakaz #{order_id}\n\n{data}",
        reply_markup=kb
    )

    bot.send_message(message.chat.id, "✅ Zakazingiz qabul qilindi.")
    users.pop(message.chat.id)


# ================= COURIER TAKE =================

@bot.callback_query_handler(func=lambda call: call.data.startswith("take_"))
def take_order(call):
    order_id = int(call.data.split("_")[1])

    couriers[call.from_user.id] = call.from_user.first_name
    stats.setdefault(call.from_user.id, 0)

    orders[order_id]["courier"] = call.from_user.id
    orders[order_id]["status"] = "taken"

    stats[call.from_user.id] += 1

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Yetkazildi", callback_data=f"done_{order_id}"))

    bot.send_message(call.from_user.id,
                     f"🚚 Siz #{order_id} zakazni oldingiz.",
                     reply_markup=kb)

    bot.answer_callback_query(call.id, "Zakaz sizga berildi")


# ================= DONE =================

@bot.callback_query_handler(func=lambda call: call.data.startswith("done_"))
def done(call):
    order_id = int(call.data.split("_")[1])
    user_id = orders[order_id]["user"]

    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        kb.add(types.InlineKeyboardButton(str(i), callback_data=f"rate_{i}_{order_id}"))

    bot.send_message(user_id, "⭐ Kuryerni baholang (1-5):", reply_markup=kb)
    bot.answer_callback_query(call.id, "Yetkazildi deb belgilandi")


# ================= RATE =================

@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def rate(call):
    rating = call.data.split("_")[1]
    order_id = call.data.split("_")[2]

    courier_id = orders[int(order_id)]["courier"]

    bot.send_message(courier_id, f"⭐ Sizga {rating} baho berildi.")
    bot.answer_callback_query(call.id, "Rahmat!")


# ================= ADMIN COMMANDS =================

@bot.message_handler(commands=['stop'])
def stop(message):
    global shop_open
    if message.chat.id == ADMIN_ID:
        shop_open = False
        bot.send_message(message.chat.id, "❌ Osh yopildi.")


@bot.message_handler(commands=['open'])
def open_shop(message):
    global shop_open
    if message.chat.id == ADMIN_ID:
        shop_open = True
        bot.send_message(message.chat.id, "✅ Osh ochildi.")


@bot.message_handler(commands=['price'])
def set_price(message):
    global osh_price
    if message.chat.id == ADMIN_ID:
        try:
            osh_price = int(message.text.split()[1])
            bot.send_message(message.chat.id, "Narx yangilandi.")
        except:
            bot.send_message(message.chat.id, "Masalan: /price 30000")


# ================= SERVER =================

if __name__ == "__main__":
    bot.remove_webhook()
    RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
    bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
