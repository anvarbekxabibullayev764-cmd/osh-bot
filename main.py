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


TOKEN=os.getenv("BOT_TOKEN")

ADMIN_ID=5915034478

COURIERS=[589856755,5915034478,710708974]

OSHKG_PRICE=45000
SALAD_PRICE=5000
CARD_NUMBER="9860 0801 8165 2332"

OSH_OPEN=True
ORDER_ID=1

logging.basicConfig(level=logging.INFO)

bot=Bot(TOKEN)
dp=Dispatcher(storage=MemoryStorage())

CLIENTS={}
CLIENT_RATING={}
USERS=set()
WAITING_RECEIPT={}

conn=sqlite3.connect("orders.db")
cursor=conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
id INTEGER,
user_id INTEGER,
total INTEGER,
status TEXT
)
""")
conn.commit()


DAILY_STATS={
 "orders":0,
 "sum":0,
 "cancel":0
}


class OrderState(StatesGroup):

 region=State()
 dom=State()
 padez=State()
 phone=State()
 location=State()
 kg=State()
 salad=State()
 payment=State()
 receipt=State()


# (MENULAR OZGARMAGAN)

def main_menu():

 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="🛒 Buyurtma berish"))

 return kb.as_markup(resize_keyboard=True)


def admin_menu():

 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="🟢 START"))
 kb.add(KeyboardButton(text="🔴 STOP"))
 kb.adjust(2)

 return kb.as_markup(resize_keyboard=True)


def region_kb():

 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="GULOBOD"))
 kb.add(KeyboardButton(text="SARXUMDON"))
 kb.adjust(2)

 return kb.as_markup()


def payment_kb():

 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="💳 Karta"))
 kb.add(KeyboardButton(text="💵 Naqd"))
 kb.adjust(2)

 return kb.as_markup()


def admin_confirm_kb(id):

 kb=InlineKeyboardBuilder()

 kb.button(text="✅ Tasdiqlash",callback_data=f"admin_yes_{id}")
 kb.button(text="❌ Bekor",callback_data=f"admin_no_{id}")

 return kb.as_markup()


def courier_kb(id):

 kb=InlineKeyboardBuilder()
 kb.button(text="🚚 Qabul qilish",callback_data=f"take_{id}")
 return kb.as_markup()


def done_kb(id):

 kb=InlineKeyboardBuilder()
 kb.button(text="✅ Yetkazildi",callback_data=f"done_{id}")
 return kb.as_markup()


def client_confirm_kb(id):

 kb=InlineKeyboardBuilder()
 kb.button(text="✅ Oldim",callback_data=f"oldim_{id}")
 return kb.as_markup()


# START OZGARMAGAN

@dp.message(Command("start"))
async def start(m:Message):

 if m.from_user.id==ADMIN_ID:
  await m.answer("Admin panel",reply_markup=admin_menu())
  return

 text=f"""
🍽 Gulobod osh bot

⚖ 1 kg osh = {OSHKG_PRICE}
🥗 Salat = {SALAD_PRICE}

🚚 Yetkazish bepul
"""

 await m.answer(text,reply_markup=main_menu())


# BUYURTMA OZGARMAGAN

# ...

# YES OZGARMAGAN + TIMER

@dp.callback_query(F.data=="yes")
async def yes(call:CallbackQuery,state:FSMContext):

 data=await state.get_data()

 CLIENTS[data["id"]]=data["user_id"]

 USERS.add(data["user_id"])

 cursor.execute("INSERT INTO orders VALUES(?,?,?)",
 (data["id"],data["user_id"],data["total"],"waiting"))

 conn.commit()

 if data["payment"]=="💳 Karta":

  WAITING_RECEIPT[data["id"]]=data["user_id"]

  await state.set_state(OrderState.receipt)

  await call.message.answer(f"Karta\n{CARD_NUMBER}\nChek yuboring")

  asyncio.create_task(receipt_timer(data["id"]))

  return

 await send_admin(call,state,"❌ To'lanmagan")


# TIMER

async def receipt_timer(id):

 await asyncio.sleep(300)

 if id in WAITING_RECEIPT:

  user_id=WAITING_RECEIPT[id]

  await bot.send_message(
  user_id,
  "❌ 5 minut chek kelmadi. Zakaz bekor qilindi"
  )

  DAILY_STATS["cancel"]+=1

  del WAITING_RECEIPT[id]


# RECEIPT

@dp.message(OrderState.receipt,F.photo)
async def receipt(m:Message,state:FSMContext):

 data=await state.get_data()

 if data["id"] in WAITING_RECEIPT:
  del WAITING_RECEIPT[data["id"]]

 await bot.send_photo(
 ADMIN_ID,
 m.photo[-1].file_id,
 caption=f"Zakaz №{data['id']} chek keldi",
 reply_markup=admin_confirm_kb(data['id'])
 )

 await send_admin(m,state,"✅ To'langan")


# ADMIN YES CHECK TEKSHIRADI

@dp.callback_query(F.data.startswith("admin_yes"))
async def admin_yes(call:CallbackQuery):

 id=int(call.data.split("_")[2])

 cursor.execute("SELECT status FROM orders WHERE id=?",(id,))
 row=cursor.fetchone()

 if row and row[0]=="waiting":

  await call.answer("❌ Chek kelmagan",show_alert=True)
  return

 text=call.message.text

 for c in COURIERS:

  await bot.send_message(c,text,reply_markup=courier_kb(id))


# ADMIN CANCEL KURIYERGAHAM

@dp.callback_query(F.data.startswith("admin_no"))
async def admin_no(call:CallbackQuery):

 id=int(call.data.split("_")[2])

 DAILY_STATS["cancel"]+=1

 user_id=CLIENTS.get(id)

 if user_id:

  await bot.send_message(user_id,"❌ Admin bekor qildi")

 for c in COURIERS:

  await bot.send_message(c,f"❌ Zakaz {id} bekor qilindi")


# DONE DELETE

@dp.callback_query(F.data.startswith("done_"))
async def done(call:CallbackQuery):

 id=int(call.data.split("_")[1])

 await call.message.delete()

 user_id=CLIENTS.get(id)

 if user_id:

  await bot.send_message(
  user_id,
  "Zakazni oldingizmi?",
  reply_markup=client_confirm_kb(id)
  )


# 22:00 REMINDER OZGARMAGAN

async def reminder_22():

 while True:

  now=datetime.now()

  if now.hour==22 and now.minute==0:

   kb=ReplyKeyboardBuilder()

   kb.add(KeyboardButton(text="✅ Ha buyurtma beraman"))
   kb.add(KeyboardButton(text="❌ Yo'q"))

   for user in USERS:

    try:
     await bot.send_message(user,"🍚 Ertaga yana buyurtma berasizmi?",reply_markup=kb.as_markup(resize_keyboard=True))
    except:
     pass

   await asyncio.sleep(60)

  await asyncio.sleep(20)


async def main():

 await bot.delete_webhook(drop_pending_updates=True)

 asyncio.create_task(reminder_22())

 await dp.start_polling(bot)


if __name__=="__main__":
 asyncio.run(main())
