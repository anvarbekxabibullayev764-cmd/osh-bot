import asyncio
import logging
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

OSHKG_PRICE = 45000
SALAD_PRICE = 5000
CARD_NUMBER = "9860 0801 8165 2332"

logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())

conn = sqlite3.connect("bot.db")
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS orders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
username TEXT,
region TEXT,
dom TEXT,
padez TEXT,
phone TEXT,
location TEXT,
kg REAL,
salad_qty INTEGER,
total INTEGER,
payment_type TEXT,
status TEXT,
created_at TEXT)""")

conn.commit()


class OrderState(StatesGroup):
    region = State()
    dom = State()
    padez = State()
    phone = State()
    location = State()
    kg = State()
    salad = State()
    payment = State()
    receipt = State()


# MENYU
def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="🛒 Buyurtma berish"))
    return kb.as_markup(resize_keyboard=True)


def region_kb():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="GULOBOD"))
    kb.add(KeyboardButton(text="SARXUMDON"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def payment_kb():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="💳 Karta"))
    kb.add(KeyboardButton(text="💵 Naqd"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def confirm_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data="confirm_yes")
    kb.button(text="❌ Bekor", callback_data="confirm_no")
    kb.adjust(2)
    return kb.as_markup()


# START
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Assalomu alaykum 🍽", reply_markup=main_menu())


# BUYURTMA BOSHLASH
@dp.message(F.text == "🛒 Buyurtma berish")
async def order_start(message: Message, state: FSMContext):

    await state.set_state(OrderState.region)

    await message.answer(
        "Hududni tanlang:",
        reply_markup=region_kb()
    )


@dp.message(OrderState.region)
async def region(message: Message, state: FSMContext):

    await state.update_data(region=message.text)

    await state.set_state(OrderState.dom)

    await message.answer(
        "Dom raqami:",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(OrderState.dom)
async def dom(message: Message, state: FSMContext):

    await state.update_data(dom=message.text)

    await state.set_state(OrderState.padez)

    await message.answer("Padez raqami:")


@dp.message(OrderState.padez)
async def padez(message: Message, state: FSMContext):

    await state.update_data(padez=message.text)

    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(
        text="📱 Raqam yuborish",
        request_contact=True
    ))

    await state.set_state(OrderState.phone)

    await message.answer(
        "Telefon:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )


@dp.message(OrderState.phone)
async def phone(message: Message, state: FSMContext):

    phone = message.contact.phone_number if message.contact else message.text

    await state.update_data(phone=phone)

    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(
        text="📍 Lokatsiya",
        request_location=True
    ))

    await state.set_state(OrderState.location)

    await message.answer(
        "Lokatsiya:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )


@dp.message(OrderState.location)
async def location(message: Message, state: FSMContext):

    if not message.location:
        await message.answer("📍 Tugmani bosing")
        return

    loc=f"{message.location.latitude},{message.location.longitude}"

    await state.update_data(location=loc)

    await state.set_state(OrderState.kg)

    await message.answer(
        f"Osh narxi {OSHKG_PRICE} so'm/kg\nNecha kg?",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(OrderState.kg)
async def kg(message: Message, state: FSMContext):

    await state.update_data(kg=float(message.text))

    await state.set_state(OrderState.salad)

    await message.answer("Salat kerakmi? (5 000) Masalan: Ha 2")


@dp.message(OrderState.salad)
async def salad(message: Message, state: FSMContext):

    qty=0

    if "ha" in message.text.lower():
        parts=message.text.split()
        qty=int(parts[1]) if len(parts)>1 else 1

    await state.update_data(salad_qty=qty)

    await state.set_state(OrderState.payment)

    await message.answer(
        "To'lov:",
        reply_markup=payment_kb()
    )


# TOLOV TANLASH
@dp.message(OrderState.payment)
async def payment(message: Message, state: FSMContext):

    data=await state.get_data()

    total=int(data["kg"]*OSHKG_PRICE+data["salad_qty"]*SALAD_PRICE)

    await state.update_data(total=total,payment=message.text)

    text=f"""
📦 Buyurtma

📍 {data['region']}
🏢 {data['dom']} 
🚪 {data['padez']}

📦 {data['kg']} kg
🥗 {data['salad_qty']}

💰 {total} so'm
"""

    await message.answer(
        text,
        reply_markup=confirm_kb()
    )


# TASDIQLASH
@dp.callback_query(F.data=="confirm_yes")
async def confirm_yes(call:CallbackQuery,state:FSMContext):

    await call.message.edit_reply_markup(reply_markup=None)

    data=await state.get_data()

    if data["payment"]=="💳 Karta":

        await state.set_state(OrderState.receipt)

        await call.message.answer(
            f"💳 Karta: {CARD_NUMBER}\nChek yuboring"
        )

        return

    await create_order(call,state,"❌ To'lanmagan")


# CHEK QABUL
@dp.message(OrderState.receipt, F.photo)
async def receipt(message:Message,state:FSMContext):

    await create_order(message,state,"✅ To'langan")


# BUYURTMA YARATISH
async def create_order(obj,state,pay_status):

    data=await state.get_data()

    maps=f"https://maps.google.com/?q={data['location']}"

    cur.execute("""INSERT INTO orders
    (user_id,username,region,dom,padez,phone,location,kg,salad_qty,total,payment_type,status,created_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    (obj.from_user.id,
     obj.from_user.username,
     data["region"],data["dom"],data["padez"],
     data["phone"],data["location"],
     data["kg"],data["salad_qty"],
     data["total"],
     data["payment"],
     pay_status,
     datetime.now().isoformat()))

    conn.commit()

    text=f"""
🆕 Zakaz

📍 {data['region']}
🏢 {data['dom']} 
🚪 {data['padez']}
📞 {data['phone']}

⚖️ {data['kg']} kg
💰 {data['total']} so'm

💳 {data['payment']}
{pay_status}

📍 {maps}
"""

    await bot.send_message(ADMIN_ID,text)

    await obj.answer(
        "✅ Buyurtma qabul qilindi",
        reply_markup=main_menu()
    )

    await state.clear()


# RUN
async def main():

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
