import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

ADMIN_ID = 5915034478

COURIER_IDS = [589856755, 710708974, 5915034478]

COURIER_NAMES = {
    589856755: "Ali",
    710708974: "Vali",
    5915034478: "Bek"
}

PRICE_PER_KG = 40000
CARD_NUMBER = "9860 0801 8165 2332"

users = {}
orders = {}
courier_stats = {}
courier_messages = {}
order_counter = 1
IS_OPEN = True


def send_message(chat_id, text, keyboard=None, inline=None):
    data = {"chat_id": chat_id, "text": text}

    if keyboard:
        data["reply_markup"] = keyboard
    if inline:
        data["reply_markup"] = inline

    requests.post(URL + "/sendMessage", json=data)


def send_photo(chat_id, file_id, caption=None, inline=None):
    data = {"chat_id": chat_id, "photo": file_id}
    if caption:
        data["caption"] = caption
    if inline:
        data["reply_markup"] = inline

    requests.post(URL + "/sendPhoto", json=data)


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    global order_counter, IS_OPEN

    try:
        data = request.get_json()

        # ================= CALLBACK =================
        if "callback_query" in data:
            call = data["callback_query"]
            callback_data = call["data"]
            courier_id = call["from"]["id"]

            # -------- KURYER QABUL QILDI --------
            if callback_data.startswith("take_"):

                order_id = int(callback_data.split("_")[1])

                if orders[order_id]["status"] != "new":
                    return "ok"

                orders[order_id]["status"] = "taken"
                orders[order_id]["courier"] = courier_id

                # Statistikaga qo‘shish
                if courier_id not in courier_stats:
                    courier_stats[courier_id] = {
                        "count": 0,
                        "rating_sum": 0,
                        "rating_count": 0
                    }

                courier_stats[courier_id]["count"] += 1

                # Boshqa kuryerlardan o‘chirish
                if order_id in courier_messages:
                    for c_id, msg_id in courier_messages[order_id]:
                        if c_id != courier_id:
                            requests.post(URL + "/deleteMessage", json={
                                "chat_id": c_id,
                                "message_id": msg_id
                            })

                name = COURIER_NAMES.get(courier_id, courier_id)

                send_message(ADMIN_ID,
                             f"🚚 Zakaz #{order_id} ni {name} oldi")

                send_message(orders[order_id]["client"],
                             f"🚚 Kuryer {name} yo‘lga chiqdi")

            # -------- YETKAZILDI --------
            if callback_data.startswith("done_"):

                order_id = int(callback_data.split("_")[1])
                orders[order_id]["status"] = "done"

                rating_keyboard = {
                    "keyboard": [["⭐1", "⭐2", "⭐3", "⭐4", "⭐5"]],
                    "resize_keyboard": True
                }

                send_message(orders[order_id]["client"],
                             "🚚 Zakaz yetkazildi. Baholang:",
                             rating_keyboard)

            # -------- ADMIN TASDIQLASH --------
            if callback_data.startswith("approve_"):

                order_id = int(callback_data.split("_")[1])
                finalize_order(order_id)
                send_message(ADMIN_ID, "✅ To‘lov tasdiqlandi")

            if callback_data.startswith("cancel_"):

                client_id = int(callback_data.split("_")[1])
                send_message(client_id, "❌ To‘lov rad etildi")

            return "ok"

        # ================= MESSAGE =================
        if "message" not in data:
            return "ok"

        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        # -------- ADMIN BUYRUQLAR --------
        if chat_id == ADMIN_ID:

            if text == "/stop":
                IS_OPEN = False
                send_message(chat_id, "⛔ Osh yopildi.")
                return "ok"

            if text == "/startosh":
                IS_OPEN = True
                send_message(chat_id, "✅ Osh ochildi.")
                return "ok"

            if text == "/stat":

                total = 0
                count = 0

                for o in orders.values():
                    total += o["data"]["price"]
                    count += 1

                send_message(chat_id,
                             f"📊 Zakazlar: {count}\n💰 Savdo: {total} so'm")
                return "ok"

            if text == "/couriers":

                msg = "📊 Kuryer statistikasi\n\n"

                for cid, data in courier_stats.items():

                    avg = 0
                    if data["rating_count"] > 0:
                        avg = round(data["rating_sum"] /
                                    data["rating_count"], 2)

                    name = COURIER_NAMES.get(cid, cid)

                    msg += f"{name}\n"
                    msg += f"Zakaz: {data['count']}\n"
                    msg += f"Reyting: {avg}\n\n"

                send_message(chat_id, msg)
                return "ok"

        # -------- START --------
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

        # -------- HUDUD --------
        if step == "area":
            users[chat_id]["area"] = text
            users[chat_id]["step"] = "house"
            send_message(chat_id, "🏢 Dom:")
            return "ok"

        if step == "house":
            users[chat_id]["house"] = text
            users[chat_id]["step"] = "padez"
            send_message(chat_id, "🚪 Padez:")
            return "ok"

        if step == "padez":
            users[chat_id]["padez"] = text
            users[chat_id]["step"] = "phone"
            send_message(chat_id, "📞 Telefon +998...")
            return "ok"

        if step == "phone":
            if text.startswith("+998"):
                users[chat_id]["phone"] = text
                users[chat_id]["step"] = "kg"
                send_message(chat_id, "⚖️ Necha kg?")
            return "ok"

        if step == "kg":
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
            return "ok"

        if step == "payment":

            users[chat_id]["payment"] = text

            if text == "💳 Karta":

                users[chat_id]["step"] = "chek"

                send_message(chat_id,
                             f"💳 Karta: {CARD_NUMBER}\nChek rasmini yuboring")
                return "ok"

            order_id = create_order(chat_id)
            finalize_order(order_id)
            return "ok"

        if step == "chek":

            if "photo" in message:

                file_id = message["photo"][-1]["file_id"]

                order_id = create_order(chat_id)

                inline = {
                    "inline_keyboard": [[
                        {"text": "✅ Tasdiqlash",
                         "callback_data": f"approve_{order_id}"},
                        {"text": "❌ Bekor",
                         "callback_data": f"cancel_{chat_id}"}
                    ]]
                }

                send_photo(ADMIN_ID,
                           file_id,
                           caption="💳 Chek keldi",
                           inline=inline)

                send_message(chat_id,
                             "⏳ To‘lov tasdiqlanishi kutilmoqda")

            return "ok"

        # -------- RATING --------
        if text.startswith("⭐"):

            rating = int(text.replace("⭐", ""))

            for o in orders.values():
                if o["client"] == chat_id and o["status"] == "done":
                    cid = o.get("courier")
                    if cid:
                        courier_stats[cid]["rating_sum"] += rating
                        courier_stats[cid]["rating_count"] += 1

            send_message(chat_id, "🙏 Rahmat!")
            return "ok"

        return "ok"

    except Exception as e:
        print("XATO:", e)
        return "ok"


def create_order(chat_id):
    global order_counter

    order_id = order_counter
    order_counter += 1

    orders[order_id] = {
        "client": chat_id,
        "data": users[chat_id],
        "status": "new"
    }

    return order_id


def finalize_order(order_id):

    data = orders[order_id]["data"]

    order_text = f"""
🆕 Zakaz #{order_id}

📍 {data['area']}
🏢 {data['house']}
🚪 {data['padez']}
📞 {data['phone']}
⚖️ {data['kg']} kg
💰 {data['price']} so'm
💳 {data['payment']}
"""

    inline_keyboard = {
        "inline_keyboard": [[
            {"text": "🚚 Qabul qilish",
             "callback_data": f"take_{order_id}"}
        ]]
    }

    courier_messages[order_id] = []

    for courier in COURIER_IDS:

        r = requests.post(URL + "/sendMessage", json={
            "chat_id": courier,
            "text": order_text,
            "reply_markup": inline_keyboard
        })

        msg_id = r.json()["result"]["message_id"]
        courier_messages[order_id].append((courier, msg_id))

    send_message(orders[order_id]["client"],
                 "✅ Zakaz qabul qilindi")

    users.pop(orders[order_id]["client"], None)


@app.route("/")
def home():
    return "Bot ishlayapti!"
