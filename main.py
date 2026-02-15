import os
import requests
import threading
import datetime
import time
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

ADMIN_ID = 5915034478

COURIER_IDS = [
    589856755,
    710708974,
    5915034478
]

PRICE_PER_KG = 40000
CARD_NUMBER = "9860 0801 8165 2332"  # <-- o'zingizni karta raqam

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


def send_photo(chat_id, file_id, caption=None):
    requests.post(URL + "/sendPhoto", json={
        "chat_id": chat_id,
        "photo": file_id,
        "caption": caption
    })


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    global order_counter, IS_OPEN

    data = request.get_json()

    # ===== CALLBACK =====
    if "callback_query" in data:
        call = data["callback_query"]
        courier_id = call["from"]["id"]
        callback_data = call["data"]

        if courier_id not in COURIER_IDS:
            return "ok"

        order_id = int(callback_data.split("_")[1])

        if callback_data.startswith("take_"):
            if orders[order_id]["status"] == "new":
                orders[order_id]["status"] = "taken"

                done_button = {
                    "inline_keyboard": [[
                        {
                            "text": "✅ Yetkazildi",
                            "callback_data": f"done_{order_id}"
                        }
                    ]]
                }

                send_message(courier_id,
                             f"🚚 Zakaz #{order_id} sizga biriktirildi",
                             inline=done_button)

        if callback_data.startswith("done_"):
            orders[order_id]["status"] = "done"
            client_id = orders[order_id]["client"]

            rating_keyboard = {
                "keyboard": [["⭐1", "⭐2", "⭐3", "⭐4", "⭐5"]],
                "resize_keyboard": True
            }

            send_message(client_id,
                         "🚚 Zakaz yetkazildi. Baholang:",
                         rating_keyboard)

        return "ok"

    if "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # ===== ADMIN =====
    if chat_id == ADMIN_ID:

        if text == "/stop":
            IS_OPEN = False
            send_message(chat_id, "⛔ Osh yopildi.")
            return "ok"

        if text == "/startosh":
            IS_OPEN = True
            send_message(chat_id, "✅ Osh ochildi.")
            return "ok"

    # ===== START =====
    if text == "/start":

        if not IS_OPEN:
            send_message(chat_id, "⛔ Bugungi osh tugagan.")
            return "ok"

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

    # AREA
    if step == "area":
        users[chat_id]["area"] = text
        users[chat_id]["step"] = "house"
        send_message(chat_id, "🏢 Dom:")
        return "ok"

    # HOUSE
    if step == "house":
        users[chat_id]["house"] = text
        users[chat_id]["step"] = "padez"
        send_message(chat_id, "🚪 Padez:")
        return "ok"

    # PADEZ
    if step == "padez":
        users[chat_id]["padez"] = text
        users[chat_id]["step"] = "phone"

        keyboard = {
            "keyboard": [[{
                "text": "📞 Kontakt yuborish",
                "request_contact": True
            }]],
            "resize_keyboard": True
        }

        send_message(chat_id,
                     "📞 Telefonni yuboring yoki +998 formatda yozing:",
                     keyboard)
        return "ok"

    # PHONE
    if step == "phone":

        if "contact" in message:
            users[chat_id]["phone"] = message["contact"]["phone_number"]
            users[chat_id]["step"] = "kg"
            send_message(chat_id, "⚖️ Necha kg?")
            return "ok"

        if text.startswith("+998") and len(text) == 13:
            users[chat_id]["phone"] = text
            users[chat_id]["step"] = "kg"
            send_message(chat_id, "⚖️ Necha kg?")
        else:
            send_message(chat_id, "❌ Telefon noto‘g‘ri.")
        return "ok"

    # KG
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
            send_message(chat_id, "❌ Kg ni raqam kiriting.")
        return "ok"

    # PAYMENT
    if step == "payment":

        users[chat_id]["payment"] = text

        # AGAR KARTA
        if text == "💳 Karta":
            users[chat_id]["step"] = "chek"

            send_message(chat_id,
                         f"💳 Karta raqam:\n{CARD_NUMBER}\n\nTo‘lov qilib chek rasmini yuboring.")
            return "ok"

        # AGAR NAQD
        finalize_order(chat_id)
        return "ok"

    # CHEK RASM
    if step == "chek":

        if "photo" in message:

            file_id = message["photo"][-1]["file_id"]

            # Admin ga chek
            send_photo(ADMIN_ID, file_id,
                       caption="💳 Karta to‘lov cheki")

            finalize_order(chat_id)
        else:
            send_message(chat_id, "❌ Chek rasmini yuboring.")
        return "ok"

    # RATING
    if text.startswith("⭐"):
        send_message(chat_id, "🙏 Rahmat baholaganingiz uchun!")
        return "ok"

    return "ok"


def finalize_order(chat_id):
    global order_counter

    order_id = order_counter
    order_counter += 1

    orders[order_id] = {
        "client": chat_id,
        "data": users[chat_id],
        "status": "new"
    }

    order_text = f"""
🆕 Zakaz #{order_id}

📍 {users[chat_id]['area']}
🏢 {users[chat_id]['house']}
🚪 {users[chat_id]['padez']}
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

    send_message(ADMIN_ID, order_text)

    for courier in COURIER_IDS:
        send_message(courier, order_text, inline=inline_keyboard)

    send_message(chat_id, "✅ Zakaz qabul qilindi.")

    users.pop(chat_id)


@app.route("/")
def home():
    return "Bot ishlayapti!"


# 22:00 reminder
def reminder():
    while True:
        now = datetime.datetime.now()
        if now.hour == 22 and now.minute == 0:
            for order in orders.values():
                send_message(order["client"],
                             "🌙 Ertaga osh zakaz qilasizmi? /start bosing")
            time.sleep(60)
        time.sleep(30)


threading.Thread(target=reminder).start()
