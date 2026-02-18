import asyncio
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

ADMIN_ID = 5915034478

COURIERS = {
    589856755: "Javohir",
    710708974: "Hazratillo"
}

PRICE_PER_KG = 40000
SALAT_PRICE = 5000

orders = {}
order_id_counter = 0


# ================= STATES =================
class OrderState(StatesGroup):
    branch = State()
    dom = State()
    padez = State()
    phone = State()
    location = State()
    kg = State()
    salat = State()
    payment = State()
    confirm = State()
    rate_food = State()
    rate_service = State()


# ================= START =================
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="GULOBOD")],
            [KeyboardButton(text="SAYXUMDON")]
        ],
        resize_keyboard=True
    )
    await message.answer("Filialni tanlang:", reply_markup=kb)
    await state.set_state(OrderState.branch)


# ================= BRANCH =================
@dp.message(OrderState.branch)
async def branch(message: Message, state: FSMContext):
    await state.update_data(branch=message.text)
    await message.answer("Dom raqamingiz:")
    await state.set_state(OrderState.dom)


# ================= DOM =================
@dp.message(OrderState.dom)
async def dom(message: Message, state: FSMContext):
    await state.update_data(dom=message.text)
    await message.answer("Padez raqami:")
    await state.set_state(OrderState.padez)


# ================= PADEZ =================
@dp.message(OrderState.padez)
async def padez(message: Message, state: FSMContext):
    await state.update_data(padez=message.text)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Telefon yuborish", request_contact=True)]
        ],
        resize_keyboard=True
    )
    await message.answer("Telefon raqamingiz:", reply_markup=kb)
    await state.set_state(OrderState.phone)


# ================= PHONE =================
@dp.message(OrderState.phone)
async def phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text

    await state.update_data(phone=phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Lokatsiya yuborish", request_location=True)]
        ],
        resize_keyboard=True
    )
    await message.answer("Lokatsiya yuboring:", reply_markup=kb)
    await state.set_state(OrderState.location)


# ================= LOCATION =================
@dp.message(OrderState.location)
async def location(message: Message, state: FSMContext):
    if not message.location:
        await message.answer("Iltimos lokatsiya yuboring.")
        return

    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude
    )

    await message.answer("Necha kg osh olasiz?")
    await state.set_state(OrderState.kg)


# ================= KG =================
@dp.message(OrderState.kg)
async def kg(message: Message, state: FSMContext):
    await state.update_data(kg=float(message.text))
    await message.answer("Salat olasizmi? (Ha/Yo'q)")
    await state.set_state(OrderState.salat)


# ================= SALAT =================
@dp.message(OrderState.salat)
async def salat(message: Message, state: FSMContext):
    await state.update_data(salat=message.text)
    await message.answer("To'lov turi (Naqd/Karta)")
    await state.set_state(OrderState.payment)


# ================= PAYMENT =================
@dp.message(OrderState.payment)
async def payment(message: Message, state: FSMContext):
    await state.update_data(payment=message.text)

    data = await state.get_data()
    total = float(data["kg"]) * PRICE_PER_KG
    if data["salat"].lower() == "ha":
        total += SALAT_PRICE

    await state.update_data(total=total)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ])

    await message.answer(
        f"Zakaz tasdiqlaysizmi?\n\nJami: {total:,} so'm",
        reply_markup=kb
    )
    await state.set_state(OrderState.confirm)


# ================= CONFIRM =================
@dp.callback_query(F.data == "confirm")
async def confirm(call: CallbackQuery, state: FSMContext):
    global order_id_counter
    order_id_counter += 1

    data = await state.get_data()
    orders[order_id_counter] = {
        "data": data,
        "courier": None,
        "status": "new",
        "client_id": call.from_user.id
    }

    text = f"🆕 Zakaz #{order_id_counter}\nKg: {data['kg']}\nJami: {data['total']:,}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Qabul qilish", callback_data=f"take_{order_id_counter}")]
    ])

    for courier in COURIERS:
        await bot.send_message(courier, text, reply_markup=kb)

    await call.message.answer("Zakazingiz qabul qilindi ✅")
    await state.clear()


# ================= TAKE =================
@dp.callback_query(F.data.startswith("take_"))
async def take(call: CallbackQuery):
    order_id = int(call.data.split("_")[1])

    if orders[order_id]["courier"] is not None:
        await call.answer("Bu zakaz olingan")
        return

    orders[order_id]["courier"] = call.from_user.id
    orders[order_id]["status"] = "taken"

    await call.message.edit_reply_markup(reply_markup=None)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Yetkazildi", callback_data=f"done_{order_id}")]
    ])

    await call.message.answer("Zakaz sizga biriktirildi", reply_markup=kb)


# ================= DONE =================
@dp.callback_query(F.data.startswith("done_"))
async def done(call: CallbackQuery):
    order_id = int(call.data.split("_")[1])
    client_id = orders[order_id]["client_id"]

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1"), KeyboardButton(text="2"),
             KeyboardButton(text="3"), KeyboardButton(text="4"),
             KeyboardButton(text="5")]
        ],
        resize_keyboard=True
    )

    await bot.send_message(client_id, "Oshni baholang (1-5)", reply_markup=kb)
    await dp.fsm.storage.set_state(
        bot=bot,
        chat=client_id,
        state=OrderState.rate_food
    )


# ================= RATE FOOD =================
@dp.message(OrderState.rate_food)
async def rate_food(message: Message, state: FSMContext):
    await state.update_data(food_rate=message.text)
    await message.answer("Xizmatni baholang (1-5)")
    await state.set_state(OrderState.rate_service)


# ================= RATE SERVICE =================
@dp.message(OrderState.rate_service)
async def rate_service(message: Message, state: FSMContext):
    await message.answer("⭐ Baholaganingiz uchun rahmat!")
    await state.clear()


# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
