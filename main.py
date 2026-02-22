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
CARD_NUMBER="9860 0801 8165 2332"

OSH_OPEN=True
ORDER_ID=1

logging.basicConfig(level=logging.INFO)

bot=Bot(TOKEN)
dp=Dispatcher(storage=MemoryStorage())


CLIENTS={}
CLIENT_RATING={}
ORDERS={}
TAKEN={}


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
  await m.answer("🔴 Osh yopildi")
  await daily_report()


@dp.message(F.text=="📊 Hisobot")
async def report(m:Message):

 if m.from_user.id==ADMIN_ID:
  await daily_report()


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
 kb.add(KeyboardButton(text="📱 Telefon yuborish",request_contact=True))

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

 await m.answer(f"⚖ Necha kg?\n1 kg = {OSHKG_PRICE}")


@dp.message(OrderState.kg)
async def kg(m:Message,state:FSMContext):

 await state.update_data(kg=float(m.text))

 await state.set_state(OrderState.salad)

 await m.answer(f"🥗 Salat nechta?\n1 ta = {SALAD_PRICE}")


@dp.message(OrderState.salad)
async def salad(m:Message,state:FSMContext):

 await state.update_data(salad_qty=int(m.text))

 await state.set_state(OrderState.payment)

 await m.answer("💰 To'lov:",reply_markup=payment_kb())


@dp.message(OrderState.payment)
async def payment(m:Message,state:FSMContext):

 global ORDER_ID

 data=await state.get_data()

 osh=int(data["kg"]*OSHKG_PRICE)
 salat=int(data["salad_qty"]*SALAD_PRICE)

 total=osh+salat

 await state.update_data(
 total=total,
 payment=m.text,
 id=ORDER_ID,
 user_id=m.from_user.id
 )

 ORDERS[ORDER_ID]=total

 text=f"""
📦 Zakaz №{ORDER_ID}

👤 Mijoz ID: {m.from_user.id}

📞 {data['phone']}

📍 {data['region']}

🏢 Dom:{data['dom']}
🚪 Padez:{data['padez']}

⚖ {data['kg']}kg
🥗 {data['salad_qty']}

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

 await call.answer()

 data=await state.get_data()

 CLIENTS[data["id"]]=data["user_id"]

 await call.message.edit_text("✅ Buyurtma tasdiqlandi")

 if data["payment"]=="💳 Karta":

  await state.set_state(OrderState.receipt)

  await call.message.answer(
   f"💳 Karta\n{CARD_NUMBER}\nChek yuboring"
  )

  asyncio.create_task(cancel_5min(data["id"]))
  return

 await send_admin(state)


@dp.callback_query(F.data=="no")
async def no(call:CallbackQuery,state:FSMContext):

 await call.answer()

 await call.message.edit_text("❌ Buyurtma bekor qilindi")

 await state.clear()


# ✅ CHEK QISMI (FIX)
@dp.message(OrderState.receipt,F.photo)
async def receipt(m:Message,state:FSMContext):

 data=await state.get_data()

 text=f"""
🆕 Zakaz №{data['id']}

👤 Mijoz ID: {data['user_id']}

📞 {data['phone']}

📍 {data['region']}

🏢 Dom:{data['dom']}
🚪 Padez:{data['padez']}

⚖ {data['kg']}kg
🥗 {data['salad_qty']}

💰 {data['total']}

💳 KARTA TO'LOV
"""

 await bot.send_photo(
  ADMIN_ID,
  m.photo[-1].file_id,
  caption=text,
  reply_markup=admin_confirm_kb(data['id'])
 )

 await m.answer("✅ Chek yuborildi")

 await state.clear()


async def cancel_5min(id):

 await asyncio.sleep(300)

 if id not in CLIENTS:
  return

 user=CLIENTS[id]

 await bot.send_message(user,"❌ 5 minut chek kelmadi bekor")


async def send_admin(state):

 data=await state.get_data()

 text=f"""
🆕 Zakaz №{data['id']}

👤 Mijoz ID: {data['user_id']}

📞 {data['phone']}

📍 {data['region']}

🏢 Dom:{data['dom']}
🚪 Padez:{data['padez']}

⚖ {data['kg']}kg
🥗 {data['salad_qty']}

💰 {data['total']}
"""

 await bot.send_message(
 ADMIN_ID,
 text,
 reply_markup=admin_confirm_kb(data['id'])
 )

 await state.clear()


@dp.callback_query(F.data.startswith("admin_yes"))
async def admin_yes(call:CallbackQuery):

 await call.answer()

 id=int(call.data.split("_")[2])

 text=call.message.text

 for c in COURIERS:

  await bot.send_message(
   c,
   text,
   reply_markup=courier_kb(id)
  )

 user_id=CLIENTS.get(id)

 if user_id:

  await bot.send_message(
   user_id,
   "✅ Buyurtmangiz tasdiqlandi\n🚚 Tez orada yetkaziladi"
  )

 await call.message.edit_text("✅ Tasdiqlandi")


@dp.callback_query(F.data.startswith("admin_no"))
async def admin_no(call:CallbackQuery):

 await call.answer()

 id=int(call.data.split("_")[2])

 user_id=CLIENTS.get(id)

 if user_id:

  await bot.send_message(
   user_id,
   "❌ Buyurtmangiz bekor qilindi"
  )

 await call.message.edit_text("❌ Bekor qilindi")


@dp.callback_query(F.data.startswith("take_"))
async def take(call:CallbackQuery):

 await call.answer()

 id=int(call.data.split("_")[1])

 if id in TAKEN:
  await call.answer("Band")
  return

 TAKEN[id]=call.from_user.id

 await call.message.edit_reply_markup(
 reply_markup=done_kb(id)
 )


@dp.callback_query(F.data.startswith("done_"))
async def done(call:CallbackQuery):

 await call.answer()

 id=int(call.data.split("_")[1])

 user_id=CLIENTS.get(id)

 if user_id:

  await bot.send_message(
  user_id,
  "Zakazni oldingizmi?",
  reply_markup=client_confirm_kb(id)
  )


@dp.callback_query(F.data.startswith("oldim_"))
async def oldim(call:CallbackQuery):

 await call.answer()

 CLIENT_RATING[call.from_user.id]=True

 await call.message.answer("⭐ Baholang 1-5")


@dp.message(F.text.in_(["1","2","3","4","5"]))
async def rating(m:Message):

 if m.from_user.id in CLIENT_RATING:

  await m.answer("Rahmat ⭐")

  del CLIENT_RATING[m.from_user.id]


async def daily_report():

 wb=Workbook()
 ws=wb.active

 ws.append(["Zakaz ID","Summa"])

 total=0

 for i in ORDERS:

  ws.append([i,ORDERS[i]])
  total+=ORDERS[i]

 ws.append(["Jami",total])

 file="hisobot.xlsx"

 wb.save(file)

 await bot.send_document(ADMIN_ID,open(file,"rb"))


async def main():

 await bot.delete_webhook(drop_pending_updates=True)

 await dp.start_polling(bot)



if __name__=="__main__":
 asyncio.run(main())
