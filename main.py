import asyncio
import logging
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, CallbackQuery,
    KeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

OSHKG_PRICE = 40000
SALAD_PRICE = 5000
CARD_NUMBER = "9860 0801 8165 2332"

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# ================= DATABASE =================
conn = sqlite3.connect("bot.db")
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS settings(
id INTEGER PRIMARY KEY, is_open INTEGER DEFAULT 1)""")

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
courier_id INTEGER,
rating INTEGER,
created_at TEXT)""")

cur.execute("""CREATE TABLE IF NOT EXISTS couriers(
user_id INTEGER PRIMARY KEY,
name TEXT)""")

cur.execute("INSERT OR IGNORE INTO settings(id,is_open) VALUES(1,1)")

# ====== KURIYERLAR QO‘SHILGAN ======
cur.execute("INSERT OR IGNORE INTO couriers(user_id,name) VALUES(589856755,'Javohir')")
cur.execute("INSERT OR IGNORE INTO couriers(user_id,name) VALUES(710708974,'Hazratillo')")
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
    receipt = State()

# ================= HELPERS =================
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

def payment_kb():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="💳 Karta"))
    kb.add(KeyboardButton(text="💵 Naqd"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def admin_confirm_kb(order_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"ok_{order_id}")
    kb.button(text="❌ Bekor", callback_data=f"no_{order_id}")
    kb.adjust(2)
    return kb.as_markup()

def courier_kb(order_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="🚴 Qabul qilish", callback_data=f"take_{order_id}")
    return kb.as_markup()

def delivered_kb(order_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Yetkazildi", callback_data=f"done_{order_id}")
    return kb.as_markup()

def rating_kb(order_id):
    kb = InlineKeyboardBuilder()
    for i in range(1,6):
        kb.button(text=str(i), callback_data=f"rate_{order_id}_{i}")
    kb.adjust(5)
    return kb.as_markup()

# ================= START =================
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Assalomu alaykum 🍽", reply_markup=main_menu())

# ================= ORDER FLOW =================
@dp.message(F.text == "🛒 Buyurtma berish")
async def order_start(message: Message, state: FSMContext):
    await state.set_state(OrderState.region)
    await message.answer("Hududni tanlang:", reply_markup=region_kb())

@dp.message(OrderState.region)
async def region(message: Message, state: FSMContext):
    await state.update_data(region=message.text)
    await state.set_state(OrderState.dom)
    await message.answer("Dom raqami:")

@dp.message(OrderState.dom)
async def dom(message: Message, state: FSMContext):
    await state.update_data(dom=message.text)
    await state.set_state(OrderState.padez)
    await message.answer("Padez raqami (Eshigigacha yetkaziladi):")

@dp.message(OrderState.padez)
async def padez(message: Message, state: FSMContext):
    await state.update_data(padez=message.text)
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="📱 Raqam yuborish", request_contact=True))
    await state.set_state(OrderState.phone)
    await message.answer("Telefon:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(OrderState.phone)
async def phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="📍 Lokatsiya", request_location=True))
    await state.set_state(OrderState.location)
    await message.answer("Lokatsiya:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(OrderState.location)
async def location(message: Message, state: FSMContext):
    loc = f"{message.location.latitude},{message.location.longitude}"
    await state.update_data(location=loc)
    await state.set_state(OrderState.kg)
    await message.answer(f"Osh narxi {OSHKG_PRICE} so'm/kg\nNecha kg?")

@dp.message(OrderState.kg)
async def kg(message: Message, state: FSMContext):
    await state.update_data(kg=float(message.text))
    await state.set_state(OrderState.salad)
    await message.answer(f"Salat? ({SALAD_PRICE}) Masalan: Ha 2 ta 1tasi 5 000")

@dp.message(OrderState.salad)
async def salad(message: Message, state: FSMContext):
    qty = 0
    if "ha" in message.text.lower():
        parts = message.text.split()
        qty = int(parts[1]) if len(parts)>1 else 1
    await state.update_data(salad_qty=qty)
    await state.set_state(OrderState.payment)
    await message.answer("To'lov:", reply_markup=payment_kb())

@dp.message(OrderState.payment)
async def payment(message: Message, state: FSMContext):
    data = await state.get_data()
    total = int(data["kg"]*OSHKG_PRICE + data["salad_qty"]*SALAD_PRICE)
    await state.update_data(total=total, payment=message.text)

    if message.text == "💳 Karta":
        await state.set_state(OrderState.receipt)
        await message.answer(f"Karta: {CARD_NUMBER}\nChek rasm yuboring.")
        return

    await create_order(message, state)

async def create_order(message, state, receipt_file=None):
    data = await state.get_data()

    cur.execute("""INSERT INTO orders
    (user_id,username,region,dom,padez,phone,location,kg,salad_qty,total,payment_type,status,created_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    (message.from_user.id,
     message.from_user.username,
     data["region"],data["dom"],data["padez"],
     data["phone"],data["location"],
     data["kg"],data["salad_qty"],
     data["total"],data["payment"],
     "waiting_admin",datetime.now().isoformat()))
    conn.commit()

    order_id = cur.lastrowid

    text=f"""🆕 Buyurtma #{order_id}
👤 @{message.from_user.username}
📍 {data['region']}
🏢 {data['dom']} | {data['padez']}
📞 {data['phone']}
📦 {data['kg']}kg
🥗 {data['salad_qty']}
💰 {data['total']} so'm"""

    if receipt_file:
        await bot.send_photo(ADMIN_ID, receipt_file, caption=text,
                             reply_markup=admin_confirm_kb(order_id))
    else:
        await bot.send_message(ADMIN_ID, text,
                               reply_markup=admin_confirm_kb(order_id))

    await message.answer("⏳ Admin tasdiqlashi kutilmoqda.")
    await state.clear()

@dp.message(OrderState.receipt, F.photo)
async def receipt(message: Message, state: FSMContext):
    await create_order(message, state, message.photo[-1].file_id)

# ================= ADMIN TASDIQ =================
@dp.callback_query(F.data.startswith("ok_"))
async def approve(call: CallbackQuery):
    order_id=int(call.data.split("_")[1])
    cur.execute("UPDATE orders SET status='approved' WHERE id=?",(order_id,))
    conn.commit()

    cur.execute("SELECT user_id,total FROM orders WHERE id=?",(order_id,))
    user_id,total=cur.fetchone()

    await bot.send_message(user_id,f"✅ Buyurtmangiz tasdiqlandi!\n💰 {total} so'm")

    cur.execute("SELECT user_id FROM couriers")
    for c in cur.fetchall():
        await bot.send_message(c[0],f"🚚 Buyurtma #{order_id}",
                               reply_markup=courier_kb(order_id))

    await call.message.edit_caption("✅ Tasdiqlandi")

@dp.callback_query(F.data.startswith("take_"))
async def take(call: CallbackQuery):
    order_id=int(call.data.split("_")[1])
    cur.execute("UPDATE orders SET courier_id=?,status='onway' WHERE id=?",
                (call.from_user.id,order_id))
    conn.commit()

    await call.message.edit_text("Siz qabul qildingiz",
                                 reply_markup=delivered_kb(order_id))
    await bot.send_message(ADMIN_ID,f"🚴 {call.from_user.id} #{order_id} oldi")

@dp.callback_query(F.data.startswith("done_"))
async def done(call: CallbackQuery):
    order_id=int(call.data.split("_")[1])
    cur.execute("UPDATE orders SET status='delivered' WHERE id=?",(order_id,))
    conn.commit()

    cur.execute("SELECT user_id FROM orders WHERE id=?",(order_id,))
    user_id=cur.fetchone()[0]

    await bot.send_message(user_id,"Buyurtmani baholang:",
                           reply_markup=rating_kb(order_id))

@dp.callback_query(F.data.startswith("rate_"))
async def rate(call: CallbackQuery):
    _,order_id,r=call.data.split("_")
    cur.execute("UPDATE orders SET rating=? WHERE id=?",(int(r),int(order_id)))
    conn.commit()
    await call.message.edit_text("Rahmat baholaganingiz uchun ⭐")
    await bot.send_message(ADMIN_ID,f"⭐ Buyurtma #{order_id} baho: {r}")

# ================= ADMIN COMMANDS =================
@dp.message(Command("stop"))
async def stop(message: Message):
    if message.from_user.id!=ADMIN_ID: return
    cur.execute("UPDATE settings SET is_open=0 WHERE id=1")
    conn.commit()
    cur.execute("SELECT COUNT(*),AVG(rating) FROM orders")
    total,avg=cur.fetchone()
    await message.answer(f"Stop\nSotildi: {total}\nO'rtacha: {avg}")

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
