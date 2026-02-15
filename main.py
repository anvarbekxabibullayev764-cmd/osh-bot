import os
import requests
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"

ADMIN_ID = 5915034478

COURIERS = {
    589856755: {"name": "Ali"},
    710708974: {"name": "Vali"},
    5915034478: {"name": "Bek"}
}

PRICE_PER_KG = 40000
CARD_NUMBER = "8600 1234 5678 9012"

IS_OPEN = True
users = {}
orders = {}
courier_stats = {}
order_counter = 1000


# ================= UTILS =================

def send(chat_id, text, keyboard=None, inline=None):
    payload = {"chat_id": chat_id, "text": text}

    if keyboard:
        payload["reply_markup"] = keyboard
    if inline:
        payload["reply_markup"] = inline

    requests.post(API + "/sendMessage", json=payload)


def send_photo(chat_id, file_id, caption=None, inline=None):
    payload = {"chat_id": chat_id, "photo": file_id}

    if caption:
        payload["caption"] = caption
    if inline:
        payload["reply_markup"] = inline

    requests.post(API + "/sendPhoto", json=payload)


def new_order(user_id):
    global order_counter
    order_counter += 1

    order_id = order_counter

    orders[order_id] = {
        "id": order_id,
        "client": user_id,
        "data": users[user_id],
        "status": "NEW",
        "courier": None,
        "created": datetime.now()
    }

    return order_id


def broadcast_to_couriers(order_id):
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
        })

        msg_id = r.json()["result"]["message_id"]
        order["courier_messages"].append((cid, msg_id))

    send(order["client"], "✅ Zakazingiz qabul qilindi.")


# ================= WEBHOOK =================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    global IS_OPEN

    try:
        update = request.get_json()

        # ========= CALLBACK =========
        if "callback_query" in update:
            call = update["callback_query"]
            data = call["data"]
            courier_id = call["from"]["id"]

            if data.startswith("take_"):
                order_id = int(data.split("_")[1])
                order = orders.get(order_id)

                if not order or order["status"] != "NEW":
                    return "ok"

                order["status"] = "TAKEN"
                order["courier"] = courier_id

                if courier_id not in courier_stats:
                    courier_stats[courier_id] = {
                        "count": 0,
                        "rating": 0,
                        "rates": 0
                    }

                courier_stats[courier_id]["count"] += 1

                # delete others
                for cid, mid in order["courier_messages"]:
                    if cid != courier_id:
                        requests.post(API + "/deleteMessage", json={
                            "chat_id": cid,
                            "message_id": mid
                        })

                name = COURIERS[courier_id]["name"]

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

                send(courier_id,
                     f"Zakaz #{order_id}",
                     inline=inline)

            if data.startswith("done_"):
                order_id = int(data.split("_")[1])
                order = orders[order_id]
                order["status"] = "DONE"

                keyboard = {
                    "keyboard": [["⭐1","⭐2","⭐3","⭐4","⭐5"]],
                    "resize_keyboard": True
                }

                send(order["client"],
                     "⭐ Kuryerni baholang:",
                     keyboard)

            if data.startswith("approve_"):
                order_id = int(data.split("_")[1])
                broadcast_to_couriers(order_id)

            return "ok"

        # ========= MESSAGE =========
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        # ========= ADMIN =========
        if chat_id == ADMIN_ID:

            if text == "/stop":
                IS_OPEN = False
                send(chat_id, "⛔ Osh yopildi")
                return "ok"

            if text == "/startosh":
                IS_OPEN = True
                send(chat_id, "✅ Osh ochildi")
                return "ok"

            if text == "/stat":
                total = sum(o["data"]["price"] for o in orders.values())
                send(chat_id,
                     f"Zakaz: {len(orders)}\nSavdo: {total} so'm")
                return "ok"

        # ========= START =========
        if text == "/start":

            if not IS_OPEN:
                send(chat_id, "⛔ Hozir yopiq")
                return "ok"

            users[chat_id] = {"step": "area"}

            keyboard = {
                "keyboard": [["📍 Gulobod"],["📍 Sarhundon"]],
                "resize_keyboard": True
            }

            send(chat_id, "Hudud tanlang:", keyboard)
            return "ok"

        if chat_id not in users:
            return "ok"

        step = users[chat_id]["step"]

        # ========= AREA =========
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

            users[chat_id]["lat"]=message["location"]["latitude"]
            users[chat_id]["lon"]=message["location"]["longitude"]
            users[chat_id]["step"]="phone"

            keyboard = {
                "keyboard":[[
                    {"text":"📞 Kontakt",
                     "request_contact":True}
                ]],
                "resize_keyboard":True
            }

            send(chat_id,"Telefon yuboring yoki +998 yozing:",keyboard)
            return "ok"

        if step=="phone":
            if "contact" in message:
                phone=message["contact"]["phone_number"]
            else:
                phone=text

            if not phone.startswith("+998"):
                send(chat_id,"❗ +998 bilan kiriting")
                return "ok"

            users[chat_id]["phone"]=phone
            users[chat_id]["step"]="kg"
            send(chat_id,"Necha kg?")
            return "ok"

        if step=="kg":
            try:
                kg=float(text)
            except:
                send(chat_id,"❗ Son kiriting")
                return "ok"

            price=kg*PRICE_PER_KG
            users[chat_id]["kg"]=kg
            users[chat_id]["price"]=price
            users[chat_id]["step"]="payment"

            keyboard={
                "keyboard":[["💵 Naqd"],["💳 Karta"]],
                "resize_keyboard":True
            }

            send(chat_id,f"{price} so'm\nTo‘lov:",keyboard)
            return "ok"

        if step=="payment":
            users[chat_id]["payment"]=text
            order_id=new_order(chat_id)

            if text=="💳 Karta":
                users[chat_id]["step"]="chek"
                send(chat_id,f"Karta: {CARD_NUMBER}\nChek yuboring")
                return "ok"

            broadcast_to_couriers(order_id)
            users.pop(chat_id)
            return "ok"

        if step=="chek":
            if "photo" not in message:
                send(chat_id,"Chek rasm yuboring")
                return "ok"

            file_id=message["photo"][-1]["file_id"]
            order_id=new_order(chat_id)

            inline={
                "inline_keyboard":[[
                    {"text":"✅ Tasdiqlash",
                     "callback_data":f"approve_{order_id}"}
                ]]
            }

            send_photo(ADMIN_ID,file_id,
                       caption="Chek keldi",
                       inline=inline)

            send(chat_id,"⏳ Tasdiq kutilmoqda")
            users.pop(chat_id)
            return "ok"

        if text.startswith("⭐"):
            rate=int(text.replace("⭐",""))
            for o in orders.values():
                if o["client"]==chat_id and o["status"]=="DONE":
                    cid=o["courier"]
                    courier_stats[cid]["rating"]+=rate
                    courier_stats[cid]["rates"]+=1
            send(chat_id,"Rahmat!")
            return "ok"

        return "ok"

    except Exception as e:
        print("ERROR:",e)
        return "ok"


@app.route("/")
def home():
    return "DELIVERY SYSTEM WORKING"
