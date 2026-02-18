import asyncio
import os
import logging
import aiosqlite
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
ADMINS = [5915034478]

PRICE_PER_KG = 40000
SALAT_PRICE = 5000

BOT_ACTIVE = True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= DATABASE =================

async def init_db():
    async with aiosqlite.connect("database.db") as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            kg REAL,
            salat TEXT,
            total REAL,
            payment TEXT,
            status TEXT,
            courier_id INTEGER,
            created_at TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS couriers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            active INTEGER,
            total_orders INTEGER
        )
        """)

        # Default courierlar
        await db.execute("""
        INSERT OR IGNORE INTO couriers (id, name, active, total_orders)
        VALUES 
        (589856755, 'Javohir', 1, 0),
        (710708974, 'Hazratillo', 1, 0)
        """)

        await db.commit()

# ================= STATES =================

class OrderState(StatesGroup):
    kg = State()
    salat = State()
    payment = State()

# ================= START =================

@dp.message(Command("start"))
async def start(message: Message):
    if not BOT_ACTIVE:
        await message.answer("⛔ Hozir osh qolmadi.")
        return

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Buyurtma berish")]],
        resize_keyboard=True
    )
    await message.answer("🍽 Osh botiga xush kelibsiz", reply_markup=kb)

# ================= ORDER FLOW =================

@dp.message(F.text == "Buyurtma berish")
async def order_start(message: Message, state: FSMContext):
    await message.answer("Necha kg osh?")
    await state.set_state(OrderState.kg)

@dp.message(OrderState.kg)
async def get_kg(message: Message, state: FSMContext):
    try:
        kg = float(message.text)
        if kg <= 0:
            raise ValueError
    except:
        await message.answer("❌ To‘g‘ri son kiriting")
        return

    await state.update_data(kg=kg)
    await message.answer("Salat kerakmi? (Ha/Yo'q)")
    await state.set_state(OrderState.salat)

@dp.message(OrderState.salat)
async def get_salat(message: Message, state: FSMContext):
    salat = message.text.lower()
    if salat not in ["ha", "yo'q", "yoq"]:
        await message.answer("Ha yoki Yo'q deb yozing")
        return

    await state.update_data(salat=salat)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Naqd", callback_data="pay_cash")],
        [InlineKeyboardButton(text="Karta", callback_data="pay_card")]
    ])

    await message.answer("To'lov turi:", reply_markup=kb)
    await state.set_state(OrderState.payment)

# ================= PAYMENT =================

@dp.callback_query(F.data.in_(["pay_cash", "pay_card"]))
async def payment(call: CallbackQuery, state: FSMContext):
    try:
        payment_type = "Naqd" if call.data == "pay_cash" else "Karta"
        data = await state.get_data()

        total = data["kg"] * PRICE_PER_KG
        if data["salat"] == "ha":
            total += SALAT_PRICE

        async with aiosqlite.connect("database.db") as db:
            cursor = await db.execute("""
                INSERT INTO orders 
                (client_id, kg, salat, total, payment, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                call.from_user.id,
                data["kg"],
                data["salat"],
                total,
                payment_type,
                "waiting",
                datetime.now().isoformat()
            ))
            await db.commit()
            order_id = cursor.lastrowid

        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer(
            f"✅ Zakaz #{order_id} qabul qilindi\nJami: {total:,} so'm"
        )

        await notify_couriers(order_id, total)

    except Exception as e:
        logging.error(e)
        await call.message.answer("Xatolik yuz berdi")

    finally:
        await state.clear()

# ================= COURIER NOTIFY =================

async def notify_couriers(order_id, total):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Qabul qilish", callback_data=f"take_{order_id}")]
    ])

    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT id FROM couriers WHERE active=1") as cursor:
            couriers = await cursor.fetchall()

    for courier in couriers:
        try:
            await bot.send_message(
                courier[0],
                f"🆕 Zakaz #{order_id}\nJami: {total:,}",
                reply_markup=kb
            )
        except Exception as e:
            logging.error(e)

# ================= TAKE =================

@dp.callback_query(F.data.startswith("take_"))
async def take_order(call: CallbackQuery):
    order_id = int(call.data.split("_")[1])

    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute(
            "SELECT status FROM orders WHERE id=?",
            (order_id,)
        )
        row = await cursor.fetchone()

        if not row or row[0] != "waiting":
            await call.answer("Bu zakaz allaqachon olingan")
            return

        await db.execute("""
            UPDATE orders 
            SET status='accepted', courier_id=? 
            WHERE id=?
        """, (call.from_user.id, order_id))

        await db.execute("""
            UPDATE couriers 
            SET total_orders = total_orders + 1 
            WHERE id=?
        """, (call.from_user.id,))

        await db.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Yetkazildi", callback_data=f"done_{order_id}")]
    ])

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("🚚 Zakaz sizga biriktirildi", reply_markup=kb)

# ================= DONE =================

@dp.callback_query(F.data.startswith("done_"))
async def done_order(call: CallbackQuery):
    order_id = int(call.data.split("_")[1])

    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "UPDATE orders SET status='delivered' WHERE id=?",
            (order_id,)
        )
        await db.commit()

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("✅ Zakaz yetkazildi")

# ================= ADMIN =================

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMINS:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Start", callback_data="admin_on")],
        [InlineKeyboardButton(text="🔴 Stop", callback_data="admin_off")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")]
    ])

    await message.answer("Admin panel", reply_markup=kb)

@dp.callback_query(F.data == "admin_on")
async def admin_on(call: CallbackQuery):
    global BOT_ACTIVE
    BOT_ACTIVE = True
    await call.message.answer("Bot ishga tushdi")

@dp.callback_query(F.data == "admin_off")
async def admin_off(call: CallbackQuery):
    global BOT_ACTIVE
    BOT_ACTIVE = False
    await call.message.answer("Bot to‘xtatildi")

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT COUNT(*) FROM orders") as cursor:
            total = (await cursor.fetchone())[0]

    await call.message.answer(f"📊 Jami zakazlar: {total}")

# ================= MAIN =================

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
