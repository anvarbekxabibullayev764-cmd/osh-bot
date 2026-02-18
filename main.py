import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from typing import List

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

OSHKG_PRICE = 40000      # 1 kg narxi
SALAD_PRICE = 5000       # 1 dona salat
CARD_NUMBER = "9860 0801 8165 2332"

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# ================= DATABASE =================
conn = sqlite3.connect("bot.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS settings(
    id INTEGER PRIMARY KEY,
    is_open INTEGER DEFAULT 1
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS orders(
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
    courier_id INTEGER,
    rating INTEGER,
    created_at TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS couriers(
    user_id INTEGER PRIMARY KEY
)
""")

cur.execute("INSERT OR IGNORE INTO settings(id,is_open) VALUES(1,1)")
conn.commit()

# ================= STATES =================
class OrderState(StatesGroup):
    region = State()
    dom = State()
    padez = State()
    phone = State()
    location = State()
    kg = State()
    salad = State()
    payment = State()
    confirm = State()

# ================= HELPERS =================
def is_open():
    cur.execute("SELECT is_open FROM settings WHERE id=1")
    return cur.fetchone()[0] == 1

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="🛒 Buyurtma berish"))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)

def region_kb():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="GULOBOD"))
    kb.add(KeyboardButton(text="SARXUMDON"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def yesno_kb():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="Ha"))
    kb.add(KeyboardButton(text="Yo'q"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def payment_kb():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="💳 Karta"))
    kb.add(KeyboardButton(text="💵 Naqd"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def courier_kb(order_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="🚴 Qabul qilish", callback_data=f"take_{order_id}")
    return kb.as_markup()

def admin_confirm_kb(order_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"admin_ok_{order_id}")
    kb.button(text="❌ Bekor qilish", callback_data=f"admin_no_{order_id}")
    kb.adjust(2)
    return kb.as_markup()

# ================= START =================
@dp.message(Command("start"))
async def start(message: Message):
    if not is_open():
        await message.answer("⛔ Hozir osh sotilmayapti.")
        return
    await message.answer("Assalomu alaykum! Xush kelibsiz 🍽", reply_markup=main_menu())

# ================= ORDER FLOW =================
@dp.message(F.text == "🛒 Buyurtma berish")
async def order_start(message: Message, state: FSMContext):
    if not is_open():
        await message.answer("⛔ Hozir osh sotilmayapti.")
        return
    await state.set_state(OrderState.region)
    await message.answer("Hududni tanlang:", reply_markup=region_kb())

@dp.message(OrderState.region)
async def region(message: Message, state: FSMContext):
    if message.text not in ["GULOBOD", "SARXUMDON"]:
        return await message.answer("Faqat tugma orqali tanlang.")
    await state.update_data(region=message.text)
    await state.set_state(OrderState.dom)
    await message.answer("Dom raqamini kiriting:")

@dp.message(OrderState.dom)
async def dom(message: Message, state: FSMContext):
    await state.update_data(dom=message.text)
    await state.set_state(OrderState.padez)
    await message.answer("Padez raqamini kiriting.\nEslatma: Padez eshigigacha yetkaziladi.")

@dp.message(OrderState.padez)
async def padez(message: Message, state: FSMContext):
    await state.update_data(padez=message.text)
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="📱 Raqam yuborish", request_contact=True))
    kb.adjust(1)
    await state.set_state(OrderState.phone)
    await message.answer("Telefon raqamingizni yuboring:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(OrderState.phone)
async def phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    await state.set_state(OrderState.location)
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="📍 Lokatsiya yuborish", request_location=True))
    kb.adjust(1)
    await message.answer("Lokatsiyani yuboring:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(OrderState.location)
async def location(message: Message, state: FSMContext):
    if not message.location:
        return await message.answer("Lokatsiyani tugma orqali yuboring.")
    loc = f"{message.location.latitude},{message.location.longitude}"
    await state.update_data(location=loc)
    await state.set_state(OrderState.kg)
    await message.answer(f"Osh narxi: {OSHKG_PRICE} so'm / 1kg\nNecha kg kerak?")

@dp.message(OrderState.kg)
async def kg(message: Message, state: FSMContext):
    try:
        kg = float(message.text)
    except:
        return await message.answer("Raqam kiriting.")
    await state.update_data(kg=kg)
    await state.set_state(OrderState.salad)
    await message.answer(f"Salat kerakmi? ({SALAD_PRICE} so'm)\nMasalan: Ha 2")

@dp.message(OrderState.salad)
async def salad(message: Message, state: FSMContext):
    text = message.text.lower()
    qty = 0
    if "ha" in text:
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit():
            qty = int(parts[1])
        else:
            qty = 1
    await state.update_data(salad_qty=qty)
    await state.set_state(OrderState.payment)
    await message.answer("To'lov turini tanlang:", reply_markup=payment_kb())

@dp.message(OrderState.payment)
async def payment(message: Message, state: FSMContext):
    if message.text not in ["💳 Karta", "💵 Naqd"]:
        return await message.answer("Faqat tugma orqali tanlang.")
    await state.update_data(payment=message.text)
    data = await state.get_data()
    total = int(data["kg"] * OSHKG_PRICE + data["salad_qty"] * SALAD_PRICE)
    await state.update_data(total=total)
    if message.text == "💳 Karta":
        await message.answer(f"Karta: <code>{CARD_NUMBER}</code>\nChek yuboring.")
    await state.set_state(OrderState.confirm)
    await message.answer(f"Jami: {total} so'm\nBuyurtmani tasdiqlaysizmi?", reply_markup=yesno_kb())

@dp.message(OrderState.confirm)
async def confirm(message: Message, state: FSMContext):
    if message.text != "Ha":
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        await state.clear()
        return
    data = await state.get_data()
    cur.execute("""
    INSERT INTO orders(user_id,username,region,dom,padez,phone,location,kg,salad_qty,total,payment_type,status,created_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        message.from_user.id,
        message.from_user.username,
        data["region"], data["dom"], data["padez"],
        data["phone"], data["location"],
        data["kg"], data["salad_qty"],
        data["total"], data["payment"],
        "pending", datetime.now().isoformat()
    ))
    conn.commit()
    order_id = cur.lastrowid
    await message.answer("✅ Buyurtma qabul qilindi.", reply_markup=main_menu())

    # Admin
    await bot.send_message(
        ADMIN_ID,
        f"🆕 Buyurtma #{order_id}\nJami: {data['total']} so'm",
        reply_markup=admin_confirm_kb(order_id)
    )
    await state.clear()

# ================= ADMIN =================
@dp.callback_query(F.data.startswith("admin_ok_"))
async def admin_ok(call: CallbackQuery):
    order_id = int(call.data.split("_")[-1])
    cur.execute("UPDATE orders SET status='approved' WHERE id=?", (order_id,))
    conn.commit()
    await call.message.edit_text(f"✅ Buyurtma #{order_id} tasdiqlandi")
    # Couriers
    cur.execute("SELECT user_id FROM couriers")
    for c in cur.fetchall():
        await bot.send_message(c[0], f"🚚 Yangi buyurtma #{order_id}", reply_markup=courier_kb(order_id))

@dp.callback_query(F.data.startswith("take_"))
async def take(call: CallbackQuery):
    order_id = int(call.data.split("_")[1])
    cur.execute("SELECT courier_id FROM orders WHERE id=?", (order_id,))
    if cur.fetchone()[0]:
        return await call.answer("Allaqachon olingan", show_alert=True)
    cur.execute("UPDATE orders SET courier_id=?, status='onway' WHERE id=?", (call.from_user.id, order_id))
    conn.commit()
    await call.message.edit_text("Siz qabul qildingiz")
    await bot.send_message(ADMIN_ID, f"🚴 Kuriyer {call.from_user.id} #{order_id} ni oldi")

# ================= ADMIN COMMANDS =================
@dp.message(Command("stop"))
async def stop(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    cur.execute("UPDATE settings SET is_open=0 WHERE id=1")
    conn.commit()
    cur.execute("SELECT COUNT(*), AVG(rating) FROM orders")
    total, avg = cur.fetchone()
    await message.answer(f"⛔ Stop\nSotildi: {total}\nO'rtacha baho: {avg}")

@dp.message(Command("startosh"))
async def startosh(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    cur.execute("UPDATE settings SET is_open=1 WHERE id=1")
    conn.commit()
    await message.answer("✅ Osh yana sotuvda")

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
