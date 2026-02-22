import asyncio
import logging
import os
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

 if m.from_user.id==ADMIN_ID:

  OSH_OPEN=False

  text=f"""
🔴 Osh yopildi

📊 Kunlik hisobot

📦 Buyurtmalar: {DAILY_STATS['orders']}
❌ Bekor qilingan: {DAILY_STATS['cancel']}
💰 Jami tushum: {DAILY_STATS['sum']}
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

 loc=f"https://maps.google.com/?q={m.location.latitude},{m.location.longitude}"

 await state.update_data(location=loc)

 await state.set_state(OrderState.kg)

 await m.answer(f"⚖ Necha kg?\n1 kg = {OSHKG_PRICE}")


@dp.message(OrderState.kg)
async def kg(m:Message,state:FSMContext):

 await state.update_data(kg=float(m.text))

 await state.set_state(OrderState.salad)

 await m.answer(f"🥗 Salat nechta?\nHa 2 yoki Yo'q")


@dp.message(OrderState.salad)
async def salad(m:Message,state:FSMContext):

 qty=0

 if "ha" in m.text.lower():
  qty=int(m.text.split()[1])

 await state.update_data(salad_qty=qty)

 await state.set_state(OrderState.payment)

 await m.answer("💰 To'lov:",reply_markup=payment_kb())


@dp.message(OrderState.payment)
async def payment(m:Message,state:FSMContext):

 global ORDER_ID

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

⚖ {data['kg']}kg
🥗 {data['salad_qty']}ta

💰 {total}

Tasdiqlaysizmi?
"""

 ORDER_ID+=1

 kb=InlineKeyboardBuilder()
 kb.button(text="✅ Tasdiqlash",callback_data="yes")
 kb.button(text="❌ Bekor",callback_data="no")

 await m.answer(text,reply_markup=kb.as_markup())


@dp.callback_query(F.data=="yes")
async def yes(call:CallbackQuery,state:FSMContext):

 data=await state.get_data()

 CLIENTS[data["id"]]=data["user_id"]

 await call.message.answer("✅ Buyurtma tasdiqlandi")

 if data["payment"]=="💳 Karta":

  await state.set_state(OrderState.receipt)

  await call.message.answer(f"Karta\n{CARD_NUMBER}\nChek yuboring")
  return

 await send_admin(call,state,"❌ To'lanmagan")


@dp.callback_query(F.data=="no")
async def cancel(call:CallbackQuery,state:FSMContext):

 DAILY_STATS["cancel"]+=1

 await call.message.answer("❌ Buyurtma bekor qilindi")

 await state.clear()

 await call.answer()


@dp.callback_query(F.data.startswith("admin_no"))
async def admin_no(call:CallbackQuery):

 id=int(call.data.split("_")[2])

 DAILY_STATS["cancel"]+=1

 user_id=CLIENTS.get(id)

 if user_id:

  await bot.send_message(
  user_id,
  "❌ Buyurtmangiz admin tomonidan bekor qilindi"
  )

 await call.message.answer("❌ Buyurtma admin tomonidan bekor qilindi")

 await call.answer()



async def send_admin(obj,state,pay):

 data=await state.get_data()

 USERS.add(data["user_id"])

 username=obj.from_user.username
 user=f"@{username}" if username else obj.from_user.first_name

 text=f"""
🆕 Zakaz №{data['id']}

👤 {user}

📞 {data['phone']}

📍 {data['region']}

🏢 Dom:{data['dom']}
🚪 Padez:{data['padez']}

📍 Lokatsiya
{data['location']}

⚖ {data['kg']}kg
🥗 {data['salad_qty']}

💰 {data['total']}

{pay}
"""

 await bot.send_message(
 ADMIN_ID,
 text,
 reply_markup=admin_confirm_kb(data['id'])
 )

 DAILY_STATS["orders"]+=1
 DAILY_STATS["sum"]+=data["total"]

 await obj.answer("Admin kutmoqda")

 await state.clear()


@dp.callback_query(F.data.startswith("admin_yes"))
async def admin_yes(call:CallbackQuery):

 id=int(call.data.split("_")[2])

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

 await call.message.answer(
 f"🚚 Kuriyer {call.from_user.first_name} zakazni oldi"
 )

 await call.message.edit_reply_markup(
 reply_markup=done_kb(id)
 )


@dp.callback_query(F.data.startswith("done_"))
async def done(call:CallbackQuery):

 id=int(call.data.split("_")[1])

 await call.message.edit_reply_markup()

 user_id=CLIENTS.get(id)

 if user_id:

  await bot.send_message(
  user_id,
  "Zakazni oldingizmi?",
  reply_markup=client_confirm_kb(id)
  )


@dp.callback_query(F.data.startswith("oldim_"))
async def oldim(call:CallbackQuery):

 CLIENT_RATING[call.from_user.id]=True

 await call.message.answer("⭐ Baholang 1-5")


@dp.message(F.text.in_(["1","2","3","4","5"]))
async def rating(m:Message):

 if m.from_user.id in CLIENT_RATING:

  await m.answer("Rahmat ⭐")

  del CLIENT_RATING[m.from_user.id]


async def reminder_22():

 while True:

  now=datetime.now()

  if now.hour==22 and now.minute==0:

   kb=ReplyKeyboardBuilder()

   kb.add(KeyboardButton(text="✅ Ha buyurtma beraman"))
   kb.add(KeyboardButton(text="❌ Yo'q"))

   kb.adjust(1)

   for user in USERS:

    try:

     await bot.send_message(
      user,
      "🍚 Ertaga yana buyurtma berasizmi?",
      reply_markup=kb.as_markup(resize_keyboard=True)
     )
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
