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

TOKEN=os.getenv("8384492890:AAFGYP-SJURZzztaYfv6tDdA1SU422FDJ7U")

ADMIN_ID=5915034478

COURIERS=[589856755,5915034478,710708974]

OSHKG_PRICE=45000
SALAD_PRICE=5000
CARD_NUMBER="9860 0801 8165 2332"

OSH_OPEN=True
ORDER_ID=1

# YANGI STATISTIKA
TOTAL_ORDERS=0
CANCELLED_ORDERS=0

logging.basicConfig(level=logging.INFO)

bot=Bot(TOKEN)
dp=Dispatcher(storage=MemoryStorage())

CLIENTS={}
CLIENT_RATING={}
TAKEN_ORDERS={}

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

 text=f"""
🍽 Gulobod osh bot

⚖ 1 kg osh = {OSHKG_PRICE}
🥗 Salat = {SALAD_PRICE}

🚚 Yetkazish bepul
"""

 await m.answer(text,reply_markup=main_menu())

@dp.message(F.text=="🟢 START")
async def start_osh(m:Message):
 global OSH_OPEN
 if m.from_user.id==ADMIN_ID:
  OSH_OPEN=True
  await m.answer("🟢 Osh ochildi")

@dp.message(F.text=="🔴 STOP")
async def stop_osh(m:Message):

 global OSH_OPEN
 global TOTAL_ORDERS
 global CANCELLED_ORDERS

 if m.from_user.id==ADMIN_ID:

  OSH_OPEN=False

  text=f"""
🔴 Osh yopildi

📦 Jami zakaz: {TOTAL_ORDERS}
❌ Admin bekor qilgan: {CANCELLED_ORDERS}
"""

  await m.answer(text)

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

 if not m.text.isdigit():
  await m.answer("❌ Faqat raqam kiriting")
  return

 await state.update_data(dom=m.text)

 await state.set_state(OrderState.padez)
 await m.answer("🚪 Padez:")

@dp.message(OrderState.padez)
async def padez(m:Message,state:FSMContext):

 if not m.text.isdigit():
  await m.answer("❌ Faqat raqam kiriting")
  return

 await state.update_data(padez=m.text)

 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="📱 Raqam",request_contact=True))

 await state.set_state(OrderState.phone)
 await m.answer("📞 Telefon:",reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(OrderState.phone)
async def phone(m:Message,state:FSMContext):

 phone=m.contact.phone_number if m.contact else m.text

 if not phone.replace("+","").isdigit():
  await m.answer("❌ Telefon noto'g'ri")
  return

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
 await m.answer(f"⚖ Necha kg?\n1 kg = {OSHKG_PRICE}",reply_markup=ReplyKeyboardRemove())

@dp.message(OrderState.kg)
async def kg(m:Message,state:FSMContext):

 if not m.text.replace(".","").isdigit():
  await m.answer("❌ Raqam kiriting")
  return

 await state.update_data(kg=float(m.text))

 await state.set_state(OrderState.salad)
 await m.answer(f"🥗 Salat nechta?\n1 ta = {SALAD_PRICE}\n0 kiriting agar yo'q")

@dp.message(OrderState.salad)
async def salad(m:Message,state:FSMContext):

 if not m.text.isdigit():
  await m.answer("❌ Raqam kiriting")
  return

 qty=int(m.text)

 await state.update_data(salad_qty=qty)

 await state.set_state(OrderState.payment)
 await m.answer("💰 To'lov:",reply_markup=payment_kb())

@dp.message(OrderState.payment)
async def payment(m:Message,state:FSMContext):

 global ORDER_ID
 global TOTAL_ORDERS

 TOTAL_ORDERS+=1

 data=await state.get_data()

 osh=int(data["kg"]*OSHKG_PRICE)
 salat=int(data["salad_qty"]*SALAD_PRICE)
 total=osh+salat

 await state.update_data(total=total,payment=m.text,id=ORDER_ID,user_id=m.from_user.id)

 text=f"""
📦 Buyurtma №{ORDER_ID}

📍 {data['region']}

🏢 Dom:{data['dom']}
🚪 Padez:{data['padez']}

⚖ {data['kg']}kg × {OSHKG_PRICE}
🥗 {data['salad_qty']}ta × {SALAD_PRICE}

💰 {total}

Tasdiqlaysizmi?
"""

 ORDER_ID+=1

 kb=InlineKeyboardBuilder()
 kb.button(text="✅ Tasdiqlash",callback_data="yes")
 kb.button(text="❌ Bekor",callback_data="no")

 await m.answer(text,reply_markup=kb.as_markup())

@dp.callback_query(F.data=="no")
async def no(call:CallbackQuery,state:FSMContext):

 await state.clear()

 await call.message.answer("❌ Buyurtma bekor qilindi",reply_markup=main_menu())

@dp.callback_query(F.data=="yes")
async def yes(call:CallbackQuery,state:FSMContext):

 data=await state.get_data()

 CLIENTS[data["id"]]=data["user_id"]

 await call.message.edit_reply_markup()

 if data["payment"]=="💳 Karta":

  await state.set_state(OrderState.receipt)

  await call.message.answer(f"💳 Karta\n{CARD_NUMBER}\nChek yuboring")

  return

 await send_admin(call,state,"❌ To'lanmagan")

@dp.callback_query(F.data.startswith("admin_no"))
async def admin_no(call:CallbackQuery):

 global CANCELLED_ORDERS

 CANCELLED_ORDERS+=1

 id=int(call.data.split("_")[2])

 user_id=CLIENTS.get(id)

 if user_id:
  await bot.send_message(user_id,"❌ Buyurtma bekor qilindi")

 await call.message.edit_reply_markup()

 await call.answer("Bekor qilindi")
