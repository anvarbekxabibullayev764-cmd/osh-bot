import os
import requests
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"

ADMIN_ID = 5915034478

# 🔁 KURYER ISMLARI ALMASHTIRILDI
COURIERS = {
    589856755: {"name": "Javohir"},
    710708974: {"name": "Hazratillo"},
    5915034478: {"name": "Bek"}
}

PRICE_PER_KG = 40000
CARD_NUMBER = "9860 0801 8165 2332"

IS_OPEN = True
users = {}
orders = {}
courier_stats = {}

# ================= ORDER COUNTER FILE SAVE =================

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

# ================= DAILY STATS =================

daily_stats = {
    "orders": 0,
    "completed": 0,
    "cancelled": 0,
    "cash": 0,
    "card": 0,
    "kg": 0,
    "revenue": 0
}

# ================= SEND FUNCTIONS =================

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

# ================= ORDER =================

def create_order(user_id):
    global order_counter
    order_counter += 1
    save_counter(order_counter)

    orders[order_counter] = {
        "id": order_counter,
        "client": user_id,
        "data": users[user_id],
        "status": "NEW",
        "courier": None,
        "created": datetime.now()
    }

    daily_stats["orders"] += 1
    daily_stats["kg"] += users[user_id]["kg"]
    daily_stats["revenue"] += users[user_id]["price"]

    if users[user_id]["payment"] == "💵 Naqd":
        daily_stats["cash"] += users[user_id]["price"]
    else:
        daily_stats["card"] += users[user_id]["price"]

    return order_counter


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

⚖️ {data['kg']} kg
💰 {data['price']} so'm
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

        # ================= CALLBACK =================
        if "callback_query" in update:
            call = update["callback_query"]
            data = call["data"]
            user_id = call["from"]["id"]

            # TAKE
            if data.startswith("take_"):
                order_id = int(data.split("_")[1])
                order = orders.get(order_id)

                if not order or order["status"] != "NEW":
                    return "ok"

                order["status"] = "TAKEN"
                order["courier"] = user_id

                for cid, mid in order["courier_messages"]:
                    if cid != user_id:
                        requests.post(API + "/deleteMessage", json={
                            "chat_id": cid,
                            "message_id": mid
                        }, timeout=10)

                name = COURIERS[user_id]["name"]

                send(ADMIN_ID,
                     f"🚚 Zakaz #{order_id} ni {name} oldi")

                send(order["client"],
                     f"🚚 Kuryer {name} yo‘lga chiqdi")

                inline = {
                    "inline_keyboard": [[
                        {"text": "✅ Yetkazildi",
                         "callback_data": f"done_{order_id}"}
                    ]]
                }

                send(user_id,
                     f"Zakaz #{order_id}",
                     inline=inline)

            # DONE
            if data.startswith("done_"):
                order_id = int(data.split("_")[1])
                orders[order_id]["status"] = "DONE"

                keyboard = {
                    "keyboard": [["⭐1","⭐2","⭐3","⭐4","⭐5"]],
                    "resize_keyboard": True,
                    "one_time_keyboard": True
                }

                send(orders[order_id]["client"],
                     "⭐ Iltimos kuryerni baholang:",
                     keyboard)

            # APPROVE CARD
            if data.startswith("approve_"):
                order_id = int(data.split("_")[1])
                send_to_couriers(order_id)
                send(orders[order_id]["client"],
                     "✅ To‘lov tasdiqlandi.")

            # CONFIRM CASH
            if data.startswith("confirm_"):
                order_id = int(data.split("_")[1])
                send_to_couriers(order_id)
                send(user_id, "✅ Buyurtma yuborildi")

            # CANCEL
            if data.startswith("cancel_"):
                order_id = int(data.split("_")[1])
                if order_id in orders:
                    daily_stats["cancelled"] += 1
                    daily_stats["revenue"] -= orders[order_id]["data"]["price"]
                orders.pop(order_id, None)
                send(user_id, "❌ Buyurtma bekor qilindi")

            return "ok"

        # ================= MESSAGE =================
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        # ================= ADMIN =================
        if chat_id == ADMIN_ID:

            if text == "/stop":
                IS_OPEN = False

                report = "📊 KUNLIK HISOBOT\n"
                report += "━━━━━━━━━━━━━━━\n\n"
                report += f"🧾 Jami zakaz: {daily_stats['orders']}\n"
                report += f"✅ Bajarildi: {daily_stats['completed']}\n"
                report += f"❌ Bekor qilindi: {daily_stats['cancelled']}\n\n"
                report += f"⚖️ Jami kg: {daily_stats['kg']} kg\n\n"
                report += f"💵 Naqd: {daily_stats['cash']} so'm\n"
                report += f"💳 Karta: {daily_stats['card']} so'm\n\n"
                report += f"💰 Umumiy savdo: {daily_stats['revenue']} so'm\n\n"

                report += "🚚 Kuryer reytingi:\n\n"

                best_name = ""
                best_rating = 0

                for cid, data in courier_stats.items():
                    avg = round(data["rating"] / data["rates"], 2) if data["rates"] else 0
                    name = COURIERS[cid]["name"]

                    report += (
                        f"{name}\n"
                        f"⭐ O‘rtacha: {avg}\n"
                        f"🧾 Baholar: {data['rates']}\n\n"
                    )

                    if avg > best_rating:
                        best_rating = avg
                        best_name = name

                if best_name:
                    report += f"🏆 Eng yaxshi kuryer: {best_name} ({best_rating})"

                send(chat_id, report)
                return "ok"

            if text == "/startosh":
                IS_OPEN = True
                send(chat_id, "✅ Osh ochildi")
                return "ok"

        # ================= START =================
        if text == "/start":
            if not IS_OPEN:
                send(chat_id, "⛔ Hozir yopiq")
                return "ok"

            users[chat_id] = {"step": "area"}

            keyboard = {
                "keyboard": [["📍 Gulobod"],["📍 Sarxumdon"]],
                "resize_keyboard": True
            }

            send(chat_id, "Hudud tanlang:", keyboard)
            return "ok"

        if chat_id not in users:
            return "ok"

        step = users[chat_id]["step"]

        if step == "area":
            users[chat_id]["area"] = text
            users[chat_id]["step"] = "house"
            send(chat_id, "🏢 Dom:")
            return "ok"

        if step == "house":
            users[chat_id]["house"] = text
            users[chat_id]["step"] = "padez"
            send(chat_id, "🚪 Padez:")
            return "ok"

        if step == "padez":
            users[chat_id]["padez"] = text
            users[chat_id]["step"] = "location"

            keyboard = {
                "keyboard":[[
                    {"text":"📍 Lokatsiya",
                     "request_location":True}
                ]],
                "resize_keyboard":True
            }

            send(chat_id,"Lokatsiyani yuboring:",keyboard)
            return "ok"

        if step == "location":
            if "location" not in message:
                send(chat_id,"❗ Tugma orqali yuboring")
                return "ok"

            users[chat_id]["lat"] = message["location"]["latitude"]
            users[chat_id]["lon"] = message["location"]["longitude"]
            users[chat_id]["step"] = "phone"

            keyboard = {
                "keyboard":[[
                    {"text":"📞 Kontakt",
                     "request_contact":True}
                ]],
                "resize_keyboard":True
            }

            send(chat_id,"Telefon yuboring:",keyboard)
            return "ok"

        if step == "phone":

            if "contact" in message:
                phone = message["contact"]["phone_number"]
                if not phone.startswith("+"):
                    phone = "+" + phone
            else:
                phone = text.strip()

            if not phone.startswith("+998") or len(phone) != 13:
                send(chat_id,"❗ To‘g‘ri kiriting: +998901234567")
                return "ok"

            users[chat_id]["phone"] = phone
            users[chat_id]["step"] = "kg"
            send(chat_id, "⚖️ Necha kg?")
            return "ok"

        if step == "kg":
            try:
                kg = float(text)
            except:
                send(chat_id,"❗ Son kiriting")
                return "ok"

            price = kg * PRICE_PER_KG
            users[chat_id]["kg"] = kg
            users[chat_id]["price"] = price
            users[chat_id]["step"] = "payment"

            keyboard = {
                "keyboard":[["💵 Naqd"],["💳 Karta"]],
                "resize_keyboard":True
            }

            send(chat_id,f"{price} so'm\nTo‘lov:",keyboard)
            return "ok"

        if step == "payment":

            users[chat_id]["payment"] = text
            order_id = create_order(chat_id)

            if text == "💳 Karta":
                users[chat_id]["step"] = "chek"
                users[chat_id]["order_id"] = order_id
                send(chat_id,f"Karta: {CARD_NUMBER}\nChek yuboring")
                return "ok"

            if text == "💵 Naqd":
                users[chat_id]["order_id"] = order_id
                users[chat_id]["step"] = "confirm_cash"

                inline = {
                    "inline_keyboard":[[
                        {"text":"✅ Ha",
                         "callback_data":f"confirm_{order_id}"},
                        {"text":"❌ Yo‘q",
                         "callback_data":f"cancel_{order_id}"}
                    ]]
                }

                send(chat_id,
                     "Buyurtmani tasdiqlaysizmi?",
                     inline=inline)
                return "ok"

        if step == "chek":
            if "photo" not in message:
                send(chat_id,"Chek rasm yuboring")
                return "ok"

            file_id = message["photo"][-1]["file_id"]
            order_id = users[chat_id]["order_id"]

            inline = {
                "inline_keyboard":[[
                    {"text":"✅ Tasdiqlash",
                     "callback_data":f"approve_{order_id}"}
                ]]
            }

            send_photo(ADMIN_ID,
                       file_id,
                       caption=f"Chek zakaz #{order_id}",
                       inline=inline)

            send(chat_id,"⏳ Tasdiq kutilmoqda")
            users.pop(chat_id)
            return "ok"

        if text.startswith("⭐"):

            rate = int(text.replace("⭐",""))

            for order_id, o in orders.items():
                if o["client"] == chat_id and o["status"] == "DONE":

                    cid = o["courier"]

                    if cid not in courier_stats:
                        courier_stats[cid] = {"rating":0,"rates":0}

                    courier_stats[cid]["rating"] += rate
                    courier_stats[cid]["rates"] += 1

                    avg = round(
                        courier_stats[cid]["rating"] /
                        courier_stats[cid]["rates"], 2
                    )

                    send(cid,
                         f"⭐ Sizga yangi baho: {rate}\n"
                         f"📊 O‘rtacha: {avg}")

                    send(ADMIN_ID,
                         f"📊 Zakaz #{order_id}\n"
                         f"Kuryer: {COURIERS[cid]['name']}\n"
                         f"Baho: {rate}\n"
                         f"O‘rtacha: {avg}")

                    daily_stats["completed"] += 1
                    orders[order_id]["status"] = "FINISHED"

                    send(chat_id,
                         "🙏 Baholaganingiz uchun rahmat!\n"
                         "Buyurtma yakunlandi ✅")

                    break

            return "ok"

        return "ok"

    except Exception as e:
        print("ERROR:", e)
        return "ok"


@app.route("/")
def home():
    return "DELIVERY SYSTEM WORKING"
    
