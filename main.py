import os
import requests
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"

ADMIN_ID = 5915034478

COURIERS = {
    589856755: {"name": "Javohir"},
    710708974: {"name": "Hazratillo"},
    5915034478: {"name": "Bek"}
}

# ===== NARXLAR =====
PRICE_PER_KG = 40000
SALAT_PRICE = 5000
CARD_NUMBER = "9860 0801 8165 2332"

IS_OPEN = True
users = {}
orders = {}
courier_stats = {}

# ===== ORDER COUNTER =====
COUNTER_FILE = "order_id.txt"

def load_counter():
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r") as f:
            return int(f.read())
    return 1000

def save_counter(value):
    with open(COUNTER_FILE, "w") as f:
        f.write(str(value))

order_counter = load_counter()

# ===== DAILY STATS =====
daily_stats = {
    "orders": 0,
    "completed": 0,
    "cancelled": 0,
    "cash": 0,
    "card": 0,
    "kg": 0,
    "revenue": 0
}

# ================= SEND =================
def send(chat_id, text, keyboard=None, inline=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = keyboard
    if inline:
        payload["reply_markup"] = inline
    requests.post(API + "/sendMessage", json=payload, timeout=10)

def send_photo(chat_id, file_id, caption=None, inline=None):
    payload = {"chat_id": chat_id, "photo": file_id}
    if caption:
        payload["caption"] = caption
    if inline:
        payload["reply_markup"] = inline
    requests.post(API + "/sendPhoto", json=payload, timeout=10)

# ================= ORDER CREATE =================
def create_order(user_id):
    global order_counter
    order_counter += 1
    save_counter(order_counter)

    data = users[user_id]

    orders[order_counter] = {
        "id": order_counter,
        "client": user_id,
        "data": data,
        "status": "NEW",
        "courier": None,
        "created": datetime.now()
    }

    daily_stats["orders"] += 1
    daily_stats["kg"] += data["kg"]
    daily_stats["revenue"] += data["total"]

    if data["payment"] == "💵 Naqd":
        daily_stats["cash"] += data["total"]
    else:
        daily_stats["card"] += data["total"]

    return order_counter

# ================= SEND TO COURIERS =================
def send_to_couriers(order_id):
    order = orders[order_id]
    data = order["data"]

    map_link = f"https://maps.google.com/?q={data['lat']},{data['lon']}"

    text = f"""
🆕 Zakaz #{order_id}

📍 {data['area']}
🏢 {data['house']}
🚪 {data['padez']}
📞 {data['phone']}

🍛 {data['kg']} kg × {PRICE_PER_KG}
🥗 Salat: {"Ha" if data["salat"] else "Yo‘q"}

💰 {data['total']} so'm
💳 {data['payment']}

🗺 {map_link}
"""

    inline = {
        "inline_keyboard": [[
            {"text": "🚚 Qabul qilish",
             "callback_data": f"take_{order_id}"}
        ]]
    }

    order["courier_messages"] = []

    for cid in COURIERS:
        r = requests.post(API + "/sendMessage", json={
            "chat_id": cid,
            "text": text,
            "reply_markup": inline
        }, timeout=10)

        msg_id = r.json()["result"]["message_id"]
        order["courier_messages"].append((cid, msg_id))

    send(order["client"], "✅ Buyurtmangiz qabul qilindi.")

# ================= WEBHOOK =================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    global IS_OPEN

    try:
        update = request.get_json()

        # ===== CALLBACK =====
        if "callback_query" in update:
            call = update["callback_query"]
            data = call["data"]
            user_id = call["from"]["id"]

            if data.startswith("salat_"):
                choice = data.split("_")[1]
                users[user_id]["salat"] = True if choice == "yes" else False

                kg = users[user_id]["kg"]
                osh_sum = kg * PRICE_PER_KG
                salat_sum = SALAT_PRICE if users[user_id]["salat"] else 0
                total = osh_sum + salat_sum

                users[user_id]["total"] = total
                users[user_id]["step"] = "payment"

                keyboard = {
                    "keyboard":[["💵 Naqd"],["💳 Karta"]],
                    "resize_keyboard":True
                }

                send(user_id,
                     f"🧾 Hisob:\n"
                     f"Osh: {osh_sum}\n"
                     f"Salat: {salat_sum}\n"
                     f"Jami: {total} so'm\n\n"
                     f"To‘lov turini tanlang:",
                     keyboard)
                return "ok"

        # ===== MESSAGE =====
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        if text == "/start":
            users[chat_id] = {"step": "kg"}
            send(chat_id, "⚖️ Necha kg osh olasiz?")
            return "ok"

        if chat_id not in users:
            return "ok"

        step = users[chat_id]["step"]

        if step == "kg":
            try:
                kg = float(text)
                if kg <= 0:
                    raise ValueError
            except:
                send(chat_id,"❗ To‘g‘ri son kiriting")
                return "ok"

            users[chat_id]["kg"] = kg
            users[chat_id]["step"] = "salat"

            inline = {
                "inline_keyboard":[[
                    {"text":"🥗 Ha","callback_data":"salat_yes"},
                    {"text":"❌ Yo‘q","callback_data":"salat_no"}
                ]]
            }

            send(chat_id,
                 "🥗 Salat ham zakaz qilasizmi? (5 000 so‘m)",
                 inline=inline)
            return "ok"

        if step == "payment":
            users[chat_id]["payment"] = text
            order_id = create_order(chat_id)

            send_to_couriers(order_id)

            users.pop(chat_id)
            return "ok"

        return "ok"

    except Exception as e:
        print("ERROR:", e)
        return "ok"

@app.route("/")
def home():
    return "DELIVERY SYSTEM WORKING 100%"
