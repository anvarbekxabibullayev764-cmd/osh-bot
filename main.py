import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
import openpyxl

TOKEN = "BOT_TOKEN"
ADMIN_ID = 123456789

logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

db = sqlite3.connect("orders.db")
sql = db.cursor()

sql.execute("""
CREATE TABLE IF NOT EXISTS orders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
name TEXT,
phone TEXT,
region TEXT,
weight TEXT,
price INTEGER,
lat TEXT,
lon TEXT,
courier INTEGER,
time TEXT
)
""")
db.commit()

# FSM
class OrderState(StatesGroup):
    name = State()
    phone = State()
    region = State()
    weight = State()
    location = State()


regions = ["Chilonzor","Yunusobod","Sergeli"]

def price_calc(w):

    w=int(w)

    if w<=5:
        return 10000
    elif w<=10:
        return 15000
    else:
        return 20000


# start
@dp.message(Command("start"))
async def start(m:Message):

    kb=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Buyurtma")]
        ],
        resize_keyboard=True
    )

    await m.answer("Assalomu alaykum",reply_markup=kb)


# buyurtma
@dp.message(F.text=="📦 Buyurtma")
async def order(m:Message,state:FSMContext):

    await m.answer("Ismingiz")
    await state.set_state(OrderState.name)


@dp.message(OrderState.name)
async def name(m:Message,state:FSMContext):

    await state.update_data(name=m.text)

    kb=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon yuborish",request_contact=True)]
        ],
        resize_keyboard=True
    )

    await m.answer("Telefon",reply_markup=kb)
    await state.set_state(OrderState.phone)


@dp.message(OrderState.phone)
async def phone(m:Message,state:FSMContext):

    phone=m.contact.phone_number

    await state.update_data(phone=phone)

    kb=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=i)] for i in regions],
        resize_keyboard=True
    )

    await m.answer("Region tanlang",reply_markup=kb)

    await state.set_state(OrderState.region)


@dp.message(OrderState.region)
async def region(m:Message,state:FSMContext):

    await state.update_data(region=m.text)

    await m.answer("Og'irlik kg")

    await state.set_state(OrderState.weight)


@dp.message(OrderState.weight)
async def weight(m:Message,state:FSMContext):

    w=m.text

    await state.update_data(weight=w)

    kb=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Lokatsiya",request_location=True)]
        ],
        resize_keyboard=True
    )

    await m.answer("Lokatsiya yuboring",reply_markup=kb)

    await state.set_state(OrderState.location)


@dp.message(OrderState.location)
async def loc(m:Message,state:FSMContext):

    data=await state.get_data()

    price=price_calc(data["weight"])

    lat=m.location.latitude
    lon=m.location.longitude

    sql.execute("""
    INSERT INTO orders(user_id,name,phone,region,weight,price,lat,lon,time)
    VALUES(?,?,?,?,?,?,?,?,?)
    """,(m.from_user.id,data["name"],data["phone"],data["region"],data["weight"],price,lat,lon,str(datetime.now())))

    db.commit()

    order_id=sql.lastrowid

    text=f"""
📦 Zakaz #{order_id}

👤 {data["name"]}
📱 {data["phone"]}

📍 {data["region"]}

⚖️ {data["weight"]}kg
💰 {price}
"""

    kb=InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚚 Olish",callback_data=f"take_{order_id}")],
            [InlineKeyboardButton(text="❌ Bekor",callback_data=f"cancel_{order_id}")]
        ]
    )

    await bot.send_message(ADMIN_ID,text,reply_markup=kb)

    await m.answer("✅ Qabul qilindi")

    await state.clear()



# courier olish
@dp.callback_query(F.data.startswith("take_"))
async def take(c:CallbackQuery):

    id=int(c.data.split("_")[1])

    sql.execute("SELECT courier FROM orders WHERE id=?",(id,))
    r=sql.fetchone()

    if r[0]:

        await c.answer("Olingan")
        return

    sql.execute("UPDATE orders SET courier=? WHERE id=?",(c.from_user.id,id))
    db.commit()

    await c.message.edit_text("🚚 Courier oldi")


# cancel
@dp.callback_query(F.data.startswith("cancel_"))
async def cancel(c:CallbackQuery):

    id=int(c.data.split("_")[1])

    await c.message.edit_text("❌ Bekor qilindi")


# hisobot
@dp.message(Command("hisobot"))
async def report(m:Message):

    wb=openpyxl.Workbook()
    ws=wb.active

    sql.execute("SELECT * FROM orders")

    for r in sql.fetchall():
        ws.append(r)

    wb.save("hisobot.xlsx")

    await m.answer_document(open("hisobot.xlsx","rb"))



async def main():

    asyncio.create_task(reminder())

    await dp.start_polling(bot)


async def reminder():

    while True:

        now=datetime.now().strftime("%H:%M")

        if now=="22:00":

            await bot.send_message(ADMIN_ID,"Hisobotni oling /hisobot")

        await asyncio.sleep(60)


if __name__=="__main__":

    asyncio.run(main())
