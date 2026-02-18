import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5915014478
COURIER_IDS = list(map(int, os.getenv("COURIER_IDS", "").split(",")))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
area TEXT,
dom TEXT,
padez TEXT,
phone TEXT,
lat TEXT,
lon TEXT,
kg REAL,
salad INTEGER,
total INTEGER,
payment TEXT,
status TEXT,
courier_id INTEGER,
rated INTEGER DEFAULT 0
)
""")
conn.commit()

PRICE_PER_KG = 40000
SALAD_PRICE = 5000
CARD_NUMBER = "9860 0801 8165 2332"

class OrderState(StatesGroup):
    area = State()
    dom = State()
    padez = State()
    phone = State()
    location = State()
    kg = State()
    salad = State()
    payment = State()
    confirm = State()
    check = State()

# START
@dp.message(F.text == "/start")
async def start_handler(message: Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="GULOBOD")],
                  [KeyboardButton(text="SAYXUMDON")]],
        resize_keyboard=True
    )
    await message.answer("Hududni tanlang:", reply_markup=kb)
    await state.set_state(OrderState.area)

@dp.message(OrderState.area)
async def area_handler(message: Message, state: FSMContext):
    await state.update_data(area=message.text)
    await message.answer("Dom raqami:")
    await state.set_state(OrderState.dom)

@dp.message(OrderState.dom)
async def dom_handler(message: Message, state: FSMContext):
    await state.update_data(dom=message.text)
    await message.answer("Padez raqami:")
    await state.set_state(OrderState.padez)

@dp.message(OrderState.padez)
async def padez_handler(message: Message, state: FSMContext):
    await state.update_data(padez=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Telefon yuborish", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer("Telefon yuboring:", reply_markup=kb)
    await state.set_state(OrderState.phone)

@dp.message(OrderState.phone)
async def phone_handler(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Lokatsiya yuborish", request_location=True)]],
        resize_keyboard=True
    )
    await message.answer("Lokatsiya yuboring:", reply_markup=kb)
    await state.set_state(OrderState.location)

@dp.message(OrderState.location)
async def location_handler(message: Message, state: FSMContext):
    await state.update_data(lat=message.location.latitude,
                            lon=message.location.longitude)
    await message.answer("Necha kg osh?")
    await state.set_state(OrderState.kg)

@dp.message(OrderState.kg)
async def kg_handler(message: Message, state: FSMContext):
    await state.update_data(kg=float(message.text))
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Ha")],
                  [KeyboardButton(text="Yo‘q")]],
        resize_keyboard=True
    )
    await message.answer("Salat olasizmi? (5000)", reply_markup=kb)
    await state.set_state(OrderState.salad)

@dp.message(OrderState.salad)
async def salad_handler(message: Message, state: FSMContext):
    salad = 1 if message.text.lower() == "ha" else 0
    await state.update_data(salad=salad)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Naqd")],
                  [KeyboardButton(text="Karta")]],
        resize_keyboard=True
    )
    await message.answer("To‘lov turi:", reply_markup=kb)
    await state.set_state(OrderState.payment)

@dp.message(OrderState.payment)
async def payment_handler(message: Message, state: FSMContext):
    await state.update_data(payment=message.text)
    data = await state.get_data()
    total = int(data["kg"] * PRICE_PER_KG + (SALAD_PRICE if data["salad"] else 0))
    await state.update_data(total=total)

    if message.text == "Karta":
        await message.answer(f"To‘lov uchun karta:\n{CARD_NUMBER}\n\nChekni yuboring:")
        await state.set_state(OrderState.check)
    else:
        await confirm_order(message, state)

async def confirm_order(message, state):
    data = await state.get_data()
    text = f"""
Zakazni tasdiqlaysizmi?

Hudud: {data['area']}
Dom: {data['dom']}
Padez: {data['padez']}
Tel: {data['phone']}
Kg: {data['kg']}
Salat: {"Ha" if data['salad'] else "Yo‘q"}
To‘lov: {data['payment']}
Jami: {data['total']} so‘m
"""
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Tasdiqlash")],
                  [KeyboardButton(text="Bekor qilish")]],
        resize_keyboard=True
    )
    await message.answer(text, reply_markup=kb)
    await state.set_state(OrderState.confirm)

@dp.message(OrderState.check, F.photo)
async def check_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("""
    INSERT INTO orders(user_id,area,dom,padez,phone,lat,lon,kg,salad,total,payment,status)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        message.from_user.id,
        data["area"], data["dom"], data["padez"],
        data["phone"], data["lat"], data["lon"],
        data["kg"], data["salad"],
        data["total"], data["payment"],
        "pending"
    ))
    conn.commit()
    order_id = cursor.lastrowid

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{order_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"reject_{order_id}")]
    ])

    await bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=f"Chek keldi\nZakaz #{order_id}\nJami: {data['total']}",
        reply_markup=kb
    )

    await message.answer("Chek yuborildi. Tasdiq kutilmoqda.")
    await state.clear()

@dp.callback_query(F.data.startswith("approve_"))
async def approve_handler(call: CallbackQuery):
    order_id = int(call.data.split("_")[1])
    cursor.execute("UPDATE orders SET status='new' WHERE id=?", (order_id,))
    conn.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚚 Qabul qilish", callback_data=f"take_{order_id}")]
    ])

    for courier in COURIER_IDS:
        await bot.send_message(courier, f"🆕 Zakaz #{order_id}", reply_markup=kb)

    await call.message.edit_caption("Tasdiqlandi va kuryerlarga yuborildi ✅")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_handler(call: CallbackQuery):
    order_id = int(call.data.split("_")[1])
    cursor.execute("SELECT user_id FROM orders WHERE id=?", (order_id,))
    user_id = cursor.fetchone()[0]

    cursor.execute("UPDATE orders SET status='rejected' WHERE id=?", (order_id,))
    conn.commit()

    await bot.send_message(user_id, "To‘lov tasdiqlanmadi ❌")
    await call.message.edit_caption("Bekor qilindi ❌")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
