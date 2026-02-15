from flask import Flask, request
import os
import requests

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text")

        if text == "/start":
            send_message(chat_id, "Assalomu alaykum! Bot ishlayapti ✅")
        else:
            send_message(chat_id, "Xabar qabul qilindi 👍")

    return "ok"

def send_message(chat_id, text):
    requests.post(URL + "sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

@app.route("/")
def home():
    return "Bot is running"
