import asyncio
import logging
import os
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

CANCELLED=0
TOTAL_KG=0
TOTAL_SALAD=0

logging.basicConfig(level=logging.INFO)

bot=Bot(TOKEN)
dp=Dispatcher(storage=MemoryStorage())

CLIENTS={}
ORDERS={}
PAYMENTS={}
ORDER_DATA={}
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


# START

@dp.message(Command("start"))
async def start(m:Message,state:FSMContext):

 await state.clear()

 if m.from_user.id==ADMIN_ID:
  await m.answer("Admin panel",reply_markup=admin_menu())
  return

 await m.answer(
 f"1kg osh={OSHKG_PRICE}\nSalat={SALAD_PRICE}",
 reply_markup=main_menu())


# START STOP

@dp.message(F.text=="🟢 START")
async def start_osh(m:Message):

 global OSH_OPEN
 OSH_OPEN=True
 await m.answer("Osh ochildi")


@dp.message(F.text=="🔴 STOP")
async def stop_osh(m:Message):

 global OSH_OPEN
 OSH_OPEN=False

 await m.answer("Osh yopildi")

 await daily_report()


@dp.message(F.text=="📊 Hisobot")
async def report(m:Message):
 await daily_report()


# BUYURTMA

@dp.message(F.text=="🛒 Buyurtma berish")
async def order(m:Message,state:FSMContext):

 if not OSH_OPEN:
  await m.answer("Osh yopiq")
  return

 await state.set_state(OrderState.region)
 await m.answer("Hudud:",reply_markup=region_kb())


@dp.message(OrderState.region)
async def region(m:Message,state:FSMContext):

 await state.update_data(region=m.text)

 await state.set_state(OrderState.dom)
 await m.answer("Dom:",reply_markup=ReplyKeyboardRemove())


@dp.message(OrderState.dom)
async def dom(m:Message,state:FSMContext):

 if not m.text.isdigit():
  await m.answer("Faqat raqam yozing")
  return

 await state.update_data(dom=m.text)

 await state.set_state(OrderState.padez)
 await m.answer("Padez:")


@dp.message(OrderState.padez)
async def padez(m:Message,state:FSMContext):

 if not m.text.isdigit():
  await m.answer("Faqat raqam yozing")
  return

 await state.update_data(padez=m.text)

 kb=ReplyKeyboardBuilder()
 kb.add(KeyboardButton(text="📱 Telefon",request_contact=True))

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


@dp.message(OrderState.location,F.location)
async def location(m:Message,state:FSMContext):

 await state.update_data(
 location=(m.location.latitude,m.location.longitude))

 await state.set_state(OrderState.kg)

 await m.answer(f"Kg kiriting\n1kg={OSHKG_PRICE}")


@dp.message(OrderState.kg)
async def kg(m:Message,state:FSMContext):

 await state.update_data(kg=float(m.text))

 await state.set_state(OrderState.salad)

 await m.answer(f"Salat nechta\n1ta={SALAD_PRICE}")


@dp.message(OrderState.salad)
async def salad(m:Message,state:FSMContext):

 await state.update_data(salad_qty=int(m.text))

 await state.set_state(OrderState.payment)

 await m.answer("Tolov:",reply_markup=payment_kb())


# TOLOV

@dp.message(OrderState.payment)
async def payment(m:Message,state:FSMContext):

 if m.text=="💳 Karta":
  await state.set_state(OrderState.check)
  await m.answer("Chek yuboring")
  return

 await finish_order(m,state,"Naqd")


# CHEK

@dp.message(OrderState.check,F.photo)
async def check(m:Message,state:FSMContext):

 global ORDER_ID

 data=await state.get_data()

 id=ORDER_ID

 data["id"]=id
 data["user_id"]=m.from_user.id

 CHECK_WAIT[id]=data

 await bot.send_photo(
 ADMIN_ID,
 m.photo[-1].file_id,
 caption=f"Chek\nZakaz:{id}",
 reply_markup=admin_confirm_kb(id))

 await m.answer("Chek yuborildi")
 await state.clear()


# ADMIN TASDIQ

@dp.callback_query(F.data.startswith("admin_yes"))
async def admin_yes(call:CallbackQuery):

 global TOTAL_KG,TOTAL_SALAD,ORDER_ID

 id=int(call.data.split("_")[2])

 data=CHECK_WAIT.get(id)

 if data:

  total=int(data["kg"]*OSHKG_PRICE)+int(data["salad_qty"]*SALAD_PRICE)

  PAYMENTS[id]="Karta"
  ORDERS[id]=total

  TOTAL_KG+=data["kg"]
  TOTAL_SALAD+=data["salad_qty"]

  text=f"""
Zakaz {id}

Kg:{data['kg']}
Salat:{data['salad_qty']}

Tolov:Karta
"""

  for c in COURIERS:
   await bot.send_message(c,text,reply_markup=courier_kb(id))

  ORDER_ID+=1

 await call.message.edit_text("Tasdiqlandi")


# ADMIN BEKOR

@dp.callback_query(F.data.startswith("admin_no"))
async def admin_no(call:CallbackQuery):

 global CANCELLED
 CANCELLED+=1

 await call.message.edit_text("Bekor qilindi")


# KURIYER

@dp.callback_query(F.data.startswith("take"))
async def take(call:CallbackQuery):

 await call.message.edit_text("Kuriyer oldi")


# NAQD

async def finish_order(m,state,payment):

 global ORDER_ID,TOTAL_KG,TOTAL_SALAD

 data=await state.get_data()

 total=int(data["kg"]*OSHKG_PRICE)+int(data["salad_qty"]*SALAD_PRICE)

 id=ORDER_ID

 PAYMENTS[id]=payment
 ORDERS[id]=total

 TOTAL_KG+=data["kg"]
 TOTAL_SALAD+=data["salad_qty"]

 ORDER_ID+=1

 text=f"""
Zakaz {id}

Kg:{data['kg']}
Salat:{data['salad_qty']}

Tolov:Naqd
"""

 await bot.send_message(
 ADMIN_ID,
 text,
 reply_markup=admin_confirm_kb(id))

 await m.answer("Qabul qilindi",reply_markup=main_menu())

 await state.clear()


# HISOBOT

async def daily_report():

 wb=Workbook()
 ws=wb.active

 ws.append(["Kg sotildi",TOTAL_KG])
 ws.append(["Salat sotildi",TOTAL_SALAD])
 ws.append(["Bekor qilingan",CANCELLED])

 wb.save("hisobot.xlsx")

 await bot.send_document(
 ADMIN_ID,
 open("hisobot.xlsx","rb"))


async def main():

 await bot.delete_webhook(drop_pending_updates=True)
 await dp.start_polling(bot)


if __name__=="__main__":
 asyncio.run(main())
