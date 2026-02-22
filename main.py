import asyncio
import logging
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, KeyboardButton
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

logging.basicConfig(level=logging.INFO)

bot=Bot(TOKEN)
dp=Dispatcher(storage=MemoryStorage())


CLIENTS={}
WAITING_RECEIPT={}
USERS=set()

DAILY_STATS={
"orders":0,
"sum":0,
"cancel":0
}


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


cursor.execute("SELECT MAX(id) FROM orders")
row=cursor.fetchone()

if row[0]:
 ORDER_ID=row[0]+1
else:
 ORDER_ID=1


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

 return kb.as_markup(resize_keyboard=True)


def payment_kb():

 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="💳 Karta"))
 kb.add(KeyboardButton(text="💵 Naqd"))
 kb.adjust(2)

 return kb.as_markup(resize_keyboard=True)


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



@dp.message(Command("start"))
async def start(m:Message):

 if m.from_user.id==ADMIN_ID:
  await m.answer("Admin panel",reply_markup=admin_menu())
  return

 await m.answer(
 f"🍽 Gulobod osh\n1kg={OSHKG_PRICE}\nSalat={SALAD_PRICE}",
 reply_markup=main_menu()
 )



@dp.message(F.text=="🛒 Buyurtma berish")
async def order_start(m:Message,state:FSMContext):

 USERS.add(m.from_user.id)

 await m.answer("Region tanlang",reply_markup=region_kb())

 await state.set_state(OrderState.region)



@dp.message(OrderState.region)
async def region(m:Message,state:FSMContext):

 await state.update_data(region=m.text)

 await m.answer("Uy raqam")

 await state.set_state(OrderState.dom)



@dp.message(OrderState.dom)
async def dom(m:Message,state:FSMContext):

 await state.update_data(dom=m.text)

 await m.answer("Padez")

 await state.set_state(OrderState.padez)



@dp.message(OrderState.padez)
async def padez(m:Message,state:FSMContext):

 await state.update_data(padez=m.text)

 await m.answer("Telefon")

 await state.set_state(OrderState.phone)



@dp.message(OrderState.phone)
async def phone(m:Message,state:FSMContext):

 await state.update_data(phone=m.text)

 await m.answer("Lokatsiya yuboring")

 await state.set_state(OrderState.location)



@dp.message(OrderState.location)
async def loc(m:Message,state:FSMContext):

 await state.update_data(location="bor")

 await m.answer("Necha kg osh")

 await state.set_state(OrderState.kg)



@dp.message(OrderState.kg)
async def kg(m:Message,state:FSMContext):

 await state.update_data(kg=int(m.text))

 await m.answer("Nechta salat")

 await state.set_state(OrderState.salad)



@dp.message(OrderState.salad)
async def salad(m:Message,state:FSMContext):

 await state.update_data(salad=int(m.text))

 await m.answer("To'lov",reply_markup=payment_kb())

 await state.set_state(OrderState.payment)



@dp.message(OrderState.payment)
async def payment(m:Message,state:FSMContext):

 global ORDER_ID

 data=await state.get_data()

 total=data["kg"]*OSHKG_PRICE+data["salad"]*SALAD_PRICE

 await state.update_data(
 id=ORDER_ID,
 total=total,
 user_id=m.from_user.id,
 payment=m.text
 )

 text=f"Zakaz {ORDER_ID}\nSumma {total}"

 kb=InlineKeyboardBuilder()
 kb.button(text="YES",callback_data="yes")

 await m.answer(text,reply_markup=kb.as_markup())

 ORDER_ID+=1



@dp.callback_query(F.data=="yes")
async def yes(call:CallbackQuery,state:FSMContext):

 data=await state.get_data()

 CLIENTS[data["id"]]=data["user_id"]

 USERS.add(data["user_id"])

 cursor.execute("INSERT INTO orders VALUES(?,?,?,?)",
 (data["id"],data["user_id"],data["total"],"waiting"))

 conn.commit()

 DAILY_STATS["orders"]+=1
 DAILY_STATS["sum"]+=data["total"]

 if data["payment"]=="💳 Karta":

  WAITING_RECEIPT[data["id"]]=data["user_id"]

  await call.message.answer(f"Karta {CARD_NUMBER}\nChek yuboring")

  await state.set_state(OrderState.receipt)

  asyncio.create_task(receipt_timer(data["id"]))

  return

 await send_admin_text(data["id"],data["total"])



async def receipt_timer(id):

 await asyncio.sleep(300)

 if id in WAITING_RECEIPT:

  user=WAITING_RECEIPT[id]

  await bot.send_message(user,"❌ 5 minut chek kelmadi")

  DAILY_STATS["cancel"]+=1

  del WAITING_RECEIPT[id]



@dp.message(OrderState.receipt,F.photo)
async def receipt(m:Message,state:FSMContext):

 data=await state.get_data()

 if data["id"] in WAITING_RECEIPT:
  del WAITING_RECEIPT[data["id"]]

 cursor.execute("UPDATE orders SET status='paid' WHERE id=?",(data["id"],))
 conn.commit()

 await bot.send_photo(
 ADMIN_ID,
 m.photo[-1].file_id,
 caption=f"Zakaz {data['id']} chek",
 reply_markup=admin_confirm_kb(data['id'])
 )



async def send_admin_text(id,total):

 await bot.send_message(
 ADMIN_ID,
 f"Zakaz {id}\nSumma {total}",
 reply_markup=admin_confirm_kb(id)
 )



@dp.callback_query(F.data.startswith("admin_yes"))
async def admin_yes(call:CallbackQuery):

 id=int(call.data.split("_")[2])

 cursor.execute("SELECT status FROM orders WHERE id=?",(id,))
 row=cursor.fetchone()

 if row[0]!="paid":
  await call.answer("Chek yo'q",show_alert=True)
  return

 for c in COURIERS:

  await bot.send_message(c,f"Zakaz {id}",reply_markup=courier_kb(id))



@dp.callback_query(F.data.startswith("admin_no"))
async def admin_no(call:CallbackQuery):

 id=int(call.data.split("_")[2])

 DAILY_STATS["cancel"]+=1

 user=CLIENTS.get(id)

 if user:
  await bot.send_message(user,"Admin bekor qildi")

 for c in COURIERS:
  await bot.send_message(c,f"Zakaz {id} bekor")



@dp.callback_query(F.data.startswith("take_"))
async def take(call:CallbackQuery):

 id=int(call.data.split("_")[1])

 await call.message.edit_reply_markup(reply_markup=done_kb(id))



@dp.callback_query(F.data.startswith("done_"))
async def done(call:CallbackQuery):

 id=int(call.data.split("_")[1])

 await call.message.delete()

 user=CLIENTS.get(id)

 if user:
  await bot.send_message(user,"Oldingizmi?",reply_markup=client_confirm_kb(id))



async def reminder_22():

 while True:

  now=datetime.now()

  if now.hour==22 and now.minute==0:

   kb=ReplyKeyboardBuilder()

   kb.add(KeyboardButton(text="✅ Ha buyurtma beraman"))
   kb.add(KeyboardButton(text="❌ Yo'q"))

   for u in USERS:

    try:
     await bot.send_message(u,"Ertaga yana osh?",reply_markup=kb.as_markup(resize_keyboard=True))
    except:
     pass

   await asyncio.sleep(60)

  await asyncio.sleep(20)



async def daily_report():

 while True:

  now=datetime.now()

  if now.hour==23 and now.minute==0:

   text=f"""
📊 Kunlik hisobot

Buyurtmalar: {DAILY_STATS['orders']}
Summa: {DAILY_STATS['sum']}
Bekor: {DAILY_STATS['cancel']}
"""

   await bot.send_message(ADMIN_ID,text)

   DAILY_STATS["orders"]=0
   DAILY_STATS["sum"]=0
   DAILY_STATS["cancel"]=0

   await asyncio.sleep(60)

  await asyncio.sleep(20)



async def main():

 await bot.delete_webhook(drop_pending_updates=True)

 asyncio.create_task(reminder_22())
 asyncio.create_task(daily_report())

 await dp.start_polling(bot)



if __name__=="__main__":
 asyncio.run(main())
