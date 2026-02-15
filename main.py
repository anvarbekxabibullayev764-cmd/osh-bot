import os
from flask import Flask, request
import requests

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 5915034478  # <-- o'zingizni yozing
OSH_PRICE = 45000

URL = f"https://api.telegram.org/bot{TOKEN}/"

users = {}

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]

    # START
    if message.get("text") == "/start":
        users[chat_id] = {"step": "address"}
        send_message(chat_id, "🏠 To‘liq manzilingizni yozing:")
        return "ok"

    if chat_id not in users:
        return "ok"

    step = users[chat_id]["step"]

    # ADDRESS
    if step == "address":
        users[chat_id]["address"] = message.get("text")
        users[chat_id]["step"] = "phone"

        keyboard = {
            "keyboard": [[{
                "text": "📱 Telefon yuborish",
                "request_contact": True
            }]],
            "resize_keyboard": True
        }

        send_message(chat_id, "📞 Telefon raqamingizni yuboring:", keyboard)
        return "ok"

    # CONTACT
    if "contact" in message:
        users[chat_id]["phone"] = message["contact"]["phone_number"]
        users[chat_id]["step"] = "portion"
        send_message(chat_id, "⚖️ Necha porsiya osh olasiz?")
        return "ok"

    # PORTION
    if step == "portion":
        if not message.get("text", "").isdigit():
            send_message(chat_id, "❗ Faqat son kiriting.")
            return "ok"

        portion = int(message["text"])
        total = portion * OSH_PRICE

        users[chat_id]["portion"] = portion
        users[chat_id]["total"] = total
        users[chat_id]["step"] = "confirm"

        text = (
            f"📍 {users[chat_id]['address']}\n"
            f"📞 {users[chat_id]['phone']}\n"
            f"🍽 {portion} porsiya\n"
            f"💰 {total} so'm\n\n"
            f"Tasdiqlaysizmi?"
        )

        keyboard = {
            "keyboard": [["✅ Ha", "❌ Yo‘q"]],
            "resize_keyboard": True
        }

        send_message(chat_id, text, keyboard)
        return "ok"

    # CONFIRM
    if step == "confirm":
        if message.get("text") == "✅ Ha":
            order = users[chat_id]

            admin_text = (
                "🆕 Yangi zakaz\n\n"
                f"📍 {order['address']}\n"
                f"📞 {order['phone']}\n"
                f"🍽 {order['portion']} porsiya\n"
                f"💰 {order['total']} so'm"
            )

            send_message(ADMIN_ID, admin_text)
            send_message(chat_id, "✅ Zakazingiz qabul qilindi 🚚")

            users.pop(chat_id)

        else:
            send_message(chat_id, "❌ Bekor qilindi.")
            users.pop(chat_id)

    return "ok"


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(URL + "sendMessage", json=payload)


@app.route("/")
def home():
    return "Bot ishlayapti 🚀"
