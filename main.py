import os
from flask import Flask, request
import requests

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

ADMIN_ID = 5915034478
COURIER_IDS = [5915034478]  # bir nechta kuryer bo‘lsa vergul bilan qo‘shing
PRICE_PER_KG = 45000

users = {}
orders = {}
order_counter = 1
IS_OPEN = True


def send_message(chat_id, text, keyboard=None, inline=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = keyboard

    if inline:
        data["reply_markup"] = inline

    requests.post(URL + "/sendMessage", json=data)


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    global order_counter, IS_OPEN

    data = request.get_json()

    # ===== CALLBACK (KURYER QABUL QILISH) =====
    if "callback_query" in data:
        call = data["callback_query"]
        courier_id = call["from"]["id"]
        order_id = int(call["data"].split("_")[1])

        if courier_id not in COURIER_IDS:
            return "ok"

        if order_id in orders and orders[order_id]["status"] == "new":
            orders[order_id]["status"] = "taken"
            orders[order_id]["courier"] = courier_id

            send_message(courier_id,
                         f"🚚 Zakaz #{order_id} sizga biriktirildi!")

        return "ok"

    if "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # ===== ADMIN BOSHQARUV =====
    if chat_id == ADMIN_ID:

        if text == "/stop":
            IS_OPEN = False
            send_message(chat_id, "⛔ Osh yopildi. Zakaz olinmaydi.")
            return "ok"

        if text == "/startosh":
            IS_OPEN = True
            send_message(chat_id, "✅ Osh ochildi. Zakaz olinadi.")
            return "ok"

    # ===== START =====
    if text == "/start":

        if not IS_OPEN:
            send_message(chat_id, "⛔ Bugungi osh tugagan.")
            return "ok"

        users.pop(chat_id, None)
        users[chat_id] = {"step": "area"}

        keyboard = {
            "keyboard": [["📍 Gulobod"], ["📍 Sarhundon"]],
            "resize_keyboard": True
        }

        send_message(chat_id, "Hududni tanlang:", keyboard)
        return "ok"

    if chat_id not in users:
        return "ok"

    step = users[chat_id]["step"]

    # ===== HUDUD =====
    if step == "area":
        users[chat_id]["area"] = text
        users[chat_id]["step"] = "house"
        send_message(chat_id, "🏢 Dom raqamini kiriting:")
        return "ok"

    # ===== DOM =====
    if step == "house":
        users[chat_id]["house"] = text
        users[chat_id]["step"] = "padez"
        send_message(chat_id, "🚪 Padez raqamini kiriting:")
        return "ok"

    # ===== PADEZ =====
    if step == "padez":
        users[chat_id]["padez"] = text
        users[chat_id]["step"] = "phone"
        send_message(chat_id, "📞 Telefon raqam (+998xxxxxxxxx):")
        return "ok"

    # ===== TELEFON =====
    if step == "phone":
        if text.startswith("+998") and len(text) == 13:
            users[chat_id]["phone"] = text
            users[chat_id]["step"] = "kg"
            send_message(chat_id, "⚖️ Necha kg olasiz?")
        else:
            send_message(chat_id, "❌ Telefon noto‘g‘ri formatda.")
        return "ok"

    # ===== KG =====
    if step == "kg":
        try:
            kg = float(text)
            price = kg * PRICE_PER_KG

            users[chat_id]["kg"] = kg
            users[chat_id]["price"] = price
            users[chat_id]["step"] = "payment"

            keyboard = {
                "keyboard": [["💵 Naqd"], ["💳 Karta"]],
                "resize_keyboard": True
            }

            send_message(chat_id,
                         f"💰 {price} so'm\nTo‘lov turini tanlang:",
                         keyboard)
        except:
            send_message(chat_id, "❌ Kg ni raqam bilan kiriting.")
        return "ok"

    # ===== TO‘LOV =====
    if step == "payment":

        if text not in ["💵 Naqd", "💳 Karta"]:
            send_message(chat_id, "To‘lov turini tanlang.")
            return "ok"

        users[chat_id]["payment"] = text

        order_id = order_counter
        order_counter += 1

        orders[order_id] = {
            "data": users[chat_id],
            "status": "new"
        }

        order_text = f"""
🆕 Zakaz #{order_id}

📍 {users[chat_id]['area']}
🏢 Dom: {users[chat_id]['house']}
🚪 Padez: {users[chat_id]['padez']}
📞 {users[chat_id]['phone']}
⚖️ {users[chat_id]['kg']} kg
💰 {users[chat_id]['price']} so'm
💳 {users[chat_id]['payment']}
"""

        inline_keyboard = {
            "inline_keyboard": [[
                {
                    "text": "🚚 Qabul qilish",
                    "callback_data": f"take_{order_id}"
                }
            ]]
        }

        # Admin ga
        send_message(ADMIN_ID, order_text)

        # Kuryerlarga
        for courier in COURIER_IDS:
            send_message(courier, order_text, inline=inline_keyboard)

        send_message(chat_id, "✅ Zakazingiz qabul qilindi.")

        users.pop(chat_id)
        return "ok"

    return "ok"


@app.route("/")
def home():
    return "Delivery bot ishlayapti!"
