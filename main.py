import asyncio
import logging
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command


TOKEN="8384492890:AAFGYP-SJURZzztaYfv6tDdA1SU422FDJ7U"

ADMIN_ID=5915034478

COURIERS=[589856755,5915034478,710708974]

OSHKG_PRICE=45000
SALAD_PRICE=5000
CARD_NUMBER="9860 0801 8165 2332"

OSH_OPEN=True
ORDER_ID=1

TOTAL_ORDER=0
CANCEL_ORDER=0


logging.basicConfig(level=logging.INFO)

bot=Bot(TOKEN)
dp=Dispatcher(storage=MemoryStorage())

CLIENTS={}
ORDERS={}


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
 "🍽 Gulobod Osh Bot\n\n"
 "🛒 Buyurtma berish tugmasini bosing",
 reply_markup=main_menu()
 )



@dp.message(F.text=="🟢 START")
async def start_osh(m:Message):

 global OSH_OPEN

 if m.from_user.id==ADMIN_ID:

  OSH_OPEN=True
  await m.answer("🟢 Osh ochildi")



@dp.message(F.text=="🔴 STOP")
async def stop_osh(m:Message):

 global OSH_OPEN

 global TOTAL_ORDER
 global CANCEL_ORDER

 if m.from_user.id==ADMIN_ID:

  OSH_OPEN=False

  await m.answer(
f"""
🔴 Osh yopildi

📊 Hisobot

📦 Zakazlar: {TOTAL_ORDER}
❌ Bekor qilingan: {CANCEL_ORDER}
"""
)



@dp.message(F.text=="🛒 Buyurtma berish")
async def order(m:Message,state:FSMContext):

 if not OSH_OPEN:

  await m.answer("❌ Osh yopiq")
  return


 await state.set_state(OrderState.region)

 await m.answer("📍 Hudud:",reply_markup=region_kb())



@dp.message(OrderState.region)
async def region(m:Message,state:FSMContext):

 await state.update_data(region=m.text)

 await state.set_state(OrderState.dom)

 await m.answer("🏢 Dom:",reply_markup=ReplyKeyboardRemove())



@dp.message(OrderState.dom)
async def dom(m:Message,state:FSMContext):

 await state.update_data(dom=m.text)

 await state.set_state(OrderState.padez)

 await m.answer("🚪 Padez:")



@dp.message(OrderState.padez)
async def padez(m:Message,state:FSMContext):

 await state.update_data(padez=m.text)

 kb=ReplyKeyboardBuilder()

 kb.add(KeyboardButton(text="📱 Raqam",request_contact=True))

 await state.set_state(OrderState.phone)

 await m.answer("📞 Telefon:",reply_markup=kb.as_markup(resize_keyboard=True))



@dp.message(OrderState.phone)
async def phone(m:Message,state:FSMContext):

 phone=m.contact.phone_number if m.contact else m.text

 await state.update_data(phone=phone)

 kb=ReplyKeyboardBuilder()

 kb.add(KeyboardButton(text="📍 Lokatsiya",request_location=True))

 await state.set_state(OrderState.location)

 await m.answer("📍 Lokatsiya:",reply_markup=kb.as_markup(resize_keyboard=True))



@dp.message(OrderState.location)
async def location(m:Message,state:FSMContext):

 loc=f"{m.location.latitude},{m.location.longitude}"

 await state.update_data(location=loc)

 await state.set_state(OrderState.kg)

 await m.answer("⚖ Necha kg?")



@dp.message(OrderState.kg)
async def kg(m:Message,state:FSMContext):

 await state.update_data(kg=float(m.text))

 await state.set_state(OrderState.salad)

 await m.answer("🥗 Salat nechta? (0 bo‘lsa 0 yozing)")



@dp.message(OrderState.salad)
async def salad(m:Message,state:FSMContext):

 await state.update_data(salad_qty=int(m.text))

 await state.set_state(OrderState.payment)

 await m.answer("💰 To'lov:",reply_markup=payment_kb())



@dp.message(OrderState.payment)
async def payment(m:Message,state:FSMContext):

 global ORDER_ID
 global TOTAL_ORDER

 data=await state.get_data()

 osh=int(data["kg"]*OSHKG_PRICE)
 salat=int(data["salad_qty"]*SALAD_PRICE)

 total=osh+salat

 await state.update_data(total=total,id=ORDER_ID,user_id=m.from_user.id)

 TOTAL_ORDER+=1

 kb=InlineKeyboardBuilder()

 kb.button(text="✅ Tasdiqlash",callback_data=f"yes_{ORDER_ID}")
 kb.button(text="❌ Bekor",callback_data=f"no_{ORDER_ID}")

 await m.answer(
f"""
📦 Zakaz №{ORDER_ID}

💰 {total}

Tasdiqlaysizmi?
""",
reply_markup=kb.as_markup()
)

 ORDER_ID+=1



@dp.callback_query(F.data.startswith("yes_"))
async def yes(call:CallbackQuery,state:FSMContext):

 data=await state.get_data()

 CLIENTS[data["id"]]=data["user_id"]

 await call.message.edit_reply_markup()

 await call.message.answer("✅ Buyurtma tasdiqlandi")

 await bot.send_message(
 ADMIN_ID,
 f"🆕 Zakaz №{data['id']}",
 reply_markup=admin_confirm_kb(data['id'])
 )

 await state.clear()



@dp.callback_query(F.data.startswith("no_"))
async def no(call:CallbackQuery):

 global CANCEL_ORDER

 CANCEL_ORDER+=1

 await call.message.edit_reply_markup()

 await call.message.answer("❌ Bekor qilindi")



@dp.callback_query(F.data.startswith("admin_no"))
async def admin_no(call:CallbackQuery):

 global CANCEL_ORDER

 id=int(call.data.split("_")[2])

 CANCEL_ORDER+=1

 user_id=CLIENTS.get(id)

 if user_id:

  await bot.send_message(user_id,"❌ Admin zakazni bekor qildi")

 await call.message.edit_reply_markup()

 await call.answer("Bekor qilindi")



async def main():

 await bot.delete_webhook(drop_pending_updates=True)

 await dp.start_polling(bot)



if __name__=="__main__":

 asyncio.run(main())
