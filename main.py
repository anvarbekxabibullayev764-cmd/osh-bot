import asyncio
import logging
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery,KeyboardButton,ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder,InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup,State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

TOKEN=os.getenv("BOT_TOKEN")

ADMIN_ID=5915034478

COURIERS={
589856755:"Javohir",
5915034478:"Anvarbek",
710708974:"Hazratillo"
}

OSHKG_PRICE=45000
SALAD_PRICE=5000
CARD_NUMBER="9860 0801 8165 2332"

logging.basicConfig(level=logging.INFO)

bot=Bot(TOKEN)
dp=Dispatcher(storage=MemoryStorage())

conn=sqlite3.connect("bot.db")
cur=conn.cursor()

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
payment TEXT,
pay_status TEXT,
status TEXT,
courier TEXT,
rating INTEGER,
created TEXT)
""")

conn.commit()


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
 rating=State()



def main_menu():
 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="🛒 Buyurtma berish"))
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
 kb.adjust(2)
 return kb.as_markup()


def courier_kb(id):
 kb=InlineKeyboardBuilder()
 kb.button(text="🚚 Qabul qilish",callback_data=f"take_{id}")
 return kb.as_markup()


def done_kb(id):
 kb=InlineKeyboardBuilder()
 kb.button(text="✅ Yetkazildi",callback_data=f"done_{id}")
 return kb.as_markup()



@dp.message(Command("start"))
async def start(m:Message):

 text="""
🍽 Gulobod osh bot

1 kg narxi 45000 so'm
Salat 5000 so'm
Yetkazish bepul
"""

 await m.answer(text,reply_markup=main_menu())



@dp.message(F.text=="🛒 Buyurtma berish")
async def order(m:Message,state:FSMContext):

 await state.set_state(OrderState.region)

 await m.answer("Hudud:",reply_markup=region_kb())



@dp.message(OrderState.region)
async def region(m:Message,state:FSMContext):

 await state.update_data(region=m.text)

 await state.set_state(OrderState.dom)

 await m.answer("Dom:",reply_markup=ReplyKeyboardRemove())



@dp.message(OrderState.dom)
async def dom(m:Message,state:FSMContext):

 await state.update_data(dom=m.text)

 await state.set_state(OrderState.padez)

 await m.answer("Padez:")



@dp.message(OrderState.padez)
async def padez(m:Message,state:FSMContext):

 await state.update_data(padez=m.text)

 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="📱 Raqam",request_contact=True))

 await state.set_state(OrderState.phone)

 await m.answer("Telefon:",reply_markup=kb.as_markup(resize_keyboard=True))



@dp.message(OrderState.phone)
async def phone(m:Message,state:FSMContext):

 phone=m.contact.phone_number if m.contact else m.text

 await state.update_data(phone=phone)

 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="📍 Lokatsiya",request_location=True))

 await state.set_state(OrderState.location)

 await m.answer("Lokatsiya:",reply_markup=kb.as_markup(resize_keyboard=True))



@dp.message(OrderState.location)
async def location(m:Message,state:FSMContext):

 loc=f"{m.location.latitude},{m.location.longitude}"

 await state.update_data(location=loc)

 await state.set_state(OrderState.kg)

 await m.answer("Necha kg?",reply_markup=ReplyKeyboardRemove())



@dp.message(OrderState.kg)
async def kg(m:Message,state:FSMContext):

 await state.update_data(kg=float(m.text))

 await state.set_state(OrderState.salad)

 await m.answer("Salat nechta? (0 bo'lsa 0 yozing)")



@dp.message(OrderState.salad)
async def salad(m:Message,state:FSMContext):

 qty=int(m.text)

 await state.update_data(salad_qty=qty)

 await state.set_state(OrderState.payment)

 await m.answer("To'lov:",reply_markup=payment_kb())



@dp.message(OrderState.payment)
async def payment(m:Message,state:FSMContext):

 data=await state.get_data()

 osh=int(data["kg"]*OSHKG_PRICE)
 salat=int(data["salad_qty"]*SALAD_PRICE)

 total=osh+salat

 await state.update_data(total=total,payment=m.text)

 text=f"""
📦 Buyurtma

📍 {data['region']}

🏢 Dom: {data['dom']}
🚪 Padez: {data['padez']}

⚖ Osh:
{data['kg']} kg

🥗 Salat:
{data['salad_qty']} ta

💰 Jami: {total}
"""

 kb=InlineKeyboardBuilder()
 kb.button(text="✅ Tasdiqlash",callback_data="yes")
 kb.button(text="❌ Bekor",callback_data="no")

 await m.answer(text,reply_markup=kb.as_markup())



@dp.callback_query(F.data=="yes")
async def yes(call:CallbackQuery,state:FSMContext):

 data=await state.get_data()

 if data["payment"]=="💳 Karta":

  await state.set_state(OrderState.receipt)

  await call.message.answer(
  f"Karta:\n{CARD_NUMBER}\nChek yuboring")

  return

 await save_order(call,state,"❌ To'lanmagan")



@dp.message(OrderState.receipt,F.photo)
async def receipt(m:Message,state:FSMContext):

 await save_order(m,state,"✅ To'langan")



async def save_order(obj,state,pay):

 data=await state.get_data()

 cur.execute("""
 INSERT INTO orders VALUES(
 NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
 """,(obj.from_user.id,
 obj.from_user.username,
 data["region"],
 data["dom"],
 data["padez"],
 data["phone"],
 data["location"],
 data["kg"],
 data["salad_qty"],
 data["total"],
 data["payment"],
 pay,
 "Kutilmoqda",
 "",
 0,
 datetime.now()))

 conn.commit()

 order_id=cur.lastrowid

 maps=f"https://maps.google.com/?q={data['location']}"

 text=f"""
🆕 Zakaz №{order_id}

👤 @{obj.from_user.username}

📞 {data['phone']}

📍 {data['region']}

🏢 Dom {data['dom']}
🚪 Padez {data['padez']}

⚖ {data['kg']} kg
🥗 {data['salad_qty']} ta

💰 {data['total']}

{data['payment']}
{pay}

{maps}
"""

 await bot.send_message(
 ADMIN_ID,
 text,
 reply_markup=admin_confirm_kb(order_id)
 )

 await obj.answer("✅ Buyurtma adminga yuborildi")

 await state.clear()



@dp.callback_query(F.data.startswith("admin_yes"))
async def admin_yes(call:CallbackQuery):

 id=int(call.data.split("_")[2])

 cur.execute("UPDATE orders SET status='Tasdiqlandi' WHERE id=?",(id,))
 conn.commit()

 text=call.message.text

 for c in COURIERS:

  await bot.send_message(
  c,
  text,
  reply_markup=courier_kb(id)
  )

 await call.answer("Kuriyerlarga yuborildi")



@dp.callback_query(F.data.startswith("take_"))
async def take(call:CallbackQuery):

 id=int(call.data.split("_")[1])

 cur.execute("UPDATE orders SET courier=? WHERE id=?",
 (COURIERS[call.from_user.id],id))

 conn.commit()

 await call.message.edit_reply_markup(
 reply_markup=done_kb(id))

 await call.answer("Qabul qilindi")



@dp.callback_query(F.data.startswith("done_"))
async def done(call:CallbackQuery,state:FSMContext):

 id=int(call.data.split("_")[1])

 await state.update_data(order_id=id)

 await state.set_state(OrderState.rating)

 await call.message.answer("⭐ Baholang 1-5")



@dp.message(OrderState.rating)
async def rating(m:Message,state:FSMContext):

 data=await state.get_data()

 cur.execute("UPDATE orders SET rating=? WHERE id=?",
 (int(m.text),data["order_id"]))

 conn.commit()

 await m.answer("Rahmat ⭐")

 await state.clear()



async def main():

 await bot.delete_webhook(drop_pending_updates=True)

 await dp.start_polling(bot)


if __name__=="__main__":
 asyncio.run(main())
