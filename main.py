import asyncio
import logging
import os
from datetime import datetime
from openpyxl import Workbook

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

OSH_OPEN=True
ORDER_ID=1

logging.basicConfig(level=logging.INFO)

bot=Bot(TOKEN)
dp=Dispatcher(storage=MemoryStorage())


CLIENTS={}
ORDERS={}
RATING_USERS={}
PAYMENTS={}
CHECK_WAIT={}


class OrderState(StatesGroup):
 region=State()
 dom=State()
 padez=State()
 phone=State()
 location=State()
 kg=State()
 salad=State()
 payment=State()
 check=State()


# MENULAR

def main_menu():
 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="🛒 Buyurtma berish"))
 return kb.as_markup(resize_keyboard=True)


def admin_menu():
 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="🟢 START"))
 kb.add(KeyboardButton(text="🔴 STOP"))
 kb.add(KeyboardButton(text="📊 Hisobot"))
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


def check_confirm_kb(id):
 kb=InlineKeyboardBuilder()
 kb.button(text="✅ Chek tasdiqlash",callback_data=f"check_yes_{id}")
 kb.button(text="❌ Bekor",callback_data=f"check_no_{id}")
 return kb.as_markup()


@dp.message(Command("start"))
async def start(m:Message,state:FSMContext):

 await state.clear()

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


# ADMIN START

@dp.message(F.text=="🟢 START")
async def start_osh(m:Message):

 global OSH_OPEN

 if m.from_user.id==ADMIN_ID:

  OSH_OPEN=True

  await m.answer("🟢 Osh ochildi")


# ADMIN STOP + HISOBOT

@dp.message(F.text=="🔴 STOP")
async def stop_osh(m:Message):

 global OSH_OPEN

 if m.from_user.id==ADMIN_ID:

  OSH_OPEN=False

  await m.answer("🔴 Osh yopildi")

  await daily_report()


# HISOBOT

@dp.message(F.text=="📊 Hisobot")
async def report(m:Message):

 if m.from_user.id==ADMIN_ID:

  await daily_report()


# BUYURTMA

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
 kb.add(KeyboardButton(text="📱 Telefon",request_contact=True))

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


@dp.message(OrderState.location,F.location)
async def location(m:Message,state:FSMContext):

 await state.update_data(
 location=(m.location.latitude,m.location.longitude)
 )

 await state.set_state(OrderState.kg)

 await m.answer(
  f"⚖ Necha kg osh kerak?\n\n"
  f"1 kg = {OSHKG_PRICE} so'm"
 )


@dp.message(OrderState.kg)
async def kg(m:Message,state:FSMContext):

 await state.update_data(kg=float(m.text))

 await state.set_state(OrderState.salad)

 await m.answer(
  f"🥗 Salat nechta?\n\n"
  f"1 ta = {SALAD_PRICE} so'm"
 )


@dp.message(OrderState.salad)
async def salad(m:Message,state:FSMContext):

 await state.update_data(salad_qty=int(m.text))

 await state.set_state(OrderState.payment)

 await m.answer("To'lov:",reply_markup=payment_kb())


# TOLOV

@dp.message(OrderState.payment)
async def payment(m:Message,state:FSMContext):

 data=await state.get_data()

 if m.text=="💳 Karta":

  CHECK_WAIT[data["id"]]=data["user_id"]

  await state.set_state(OrderState.check)

  await m.answer("💳 Chek rasmini yuboring")

  return


 payment_type="Naqd"

 await finish_order(m,state,payment_type)


# CHEK

@dp.message(OrderState.check,F.photo)
async def check(m:Message,state:FSMContext):

 data=await state.get_data()

 id=data["id"]

 CHECK_WAIT[id]=data["user_id"]

 await bot.send_photo(
 ADMIN_ID,
 m.photo[-1].file_id,
 caption=f"💳 Chek\nZakaz:{id}",
 reply_markup=check_confirm_kb(id)
 )

 await m.answer("Chek yuborildi")

 await state.clear()


@dp.callback_query(F.data.startswith("check_yes"))
async def check_yes(call:CallbackQuery):

 id=int(call.data.split("_")[2])

 PAYMENTS[id]="Karta"

 await call.message.edit_text("Chek tasdiqlandi")

 await send_to_admin(id)


async def finish_order(m,state,payment):

 global ORDER_ID

 data=await state.get_data()

 total=int(data["kg"]*OSHKG_PRICE)+int(data["salad_qty"]*SALAD_PRICE)

 id=ORDER_ID

 PAYMENTS[id]=payment

 CLIENTS[id]=m.from_user.id

 ORDERS[id]=total

 ORDER_ID+=1

 data["id"]=id
 data["total"]=total
 data["user_id"]=m.from_user.id

 await state.update_data(**data)

 await send_admin(state)

 await state.clear()

 await m.answer("Buyurtma qabul qilindi",reply_markup=main_menu())


async def send_admin(state):

 data=await state.get_data()

 lat,lon=data["location"]

 text=f"""
🆕 Zakaz №{data['id']}

👤 Mijoz ID:{data['user_id']}

📞 {data['phone']}

📍 {data['region']}
🏢 {data['dom']}
🚪 {data['padez']}

⚖ {data['kg']}kg
🥗 {data['salad_qty']}

💰 {data['total']}
"""

 await bot.send_message(
 ADMIN_ID,
 text,
 reply_markup=admin_confirm_kb(data['id'])
 )


@dp.callback_query(F.data.startswith("admin_yes"))
async def admin_yes(call:CallbackQuery):

 id=int(call.data.split("_")[2])

 payment=PAYMENTS.get(id)

 status="To'langan" if payment=="Karta" else "To'lanmagan"

 text=call.message.text+f"\n\n💰 {payment}\n📊 {status}"

 for c in COURIERS:

  await bot.send_message(
   c,
   text,
   reply_markup=courier_kb(id)
  )

 await call.message.edit_text("Admin tasdiqladi")


async def daily_report():

 wb=Workbook()
 ws=wb.active

 ws.append(["Zakaz ID","Summa"])

 total=0

 for i in ORDERS:

  ws.append([i,ORDERS[i]])

  total+=ORDERS[i]

 ws.append(["Jami",total])

 wb.save("hisobot.xlsx")

 await bot.send_document(
 ADMIN_ID,
 open("hisobot.xlsx","rb")
 )


async def main():

 await bot.delete_webhook(drop_pending_updates=True)

 await dp.start_polling(bot)


if __name__=="__main__":
 asyncio.run(main())
