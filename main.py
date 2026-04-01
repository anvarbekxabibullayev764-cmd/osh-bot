import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from PIL import Image, ImageDraw, ImageFont

# 🔐 TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5915034478

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN topilmadi")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# 📡 Kanallar
TELEGRAM_CHANNELS = [
    "@xdp_shayxontohur",
    "@olimmov_ozodbekk"
]

# 📸 Instagram
INSTAGRAM_LINKS = [
    "https://www.instagram.com/o.o.olimmov",
    "https://www.instagram.com/xdp.shayxontohur",
    "https://www.instagram.com/anvarbek.xabibullayev"
]

# 🧠 STATE
class Form(StatesGroup):
    name = State()

# 📂 TEMPLATE (markaz koordinata)
TEMPLATES = {
    "sert1": {"file": "data/template1.png", "x": 750, "y": 470, "size": 90},
    "sert2": {"file": "data/template2.png", "x": 750, "y": 520, "size": 80},
    "sert3": {"file": "data/template3.png", "x": 750, "y": 500, "size": 80},
    "sert4": {"file": "data/template4.png", "x": 750, "y": 540, "size": 80},
    "sert5": {"file": "data/template5.png", "x": 750, "y": 520, "size": 80},
    "sert6": {"file": "data/template6.png", "x": 750, "y": 530, "size": 80},
}

# 🔘 START MENU
def keyboard():
    kb = InlineKeyboardMarkup(row_width=1)

    for ch in TELEGRAM_CHANNELS:
        kb.add(InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}"))

    kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
    return kb

# 🔍 OBUNA TEKSHIRISH
async def check_sub(user_id):
    for ch in TELEGRAM_CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# 🖼️ SERTIFIKAT FUNKSIYA
def generate_certificate(name, cert_type):
    config = TEMPLATES[cert_type]

    if not os.path.exists(config["file"]):
        raise Exception(f"{cert_type} template topilmadi")

    img = Image.open(config["file"]).convert("RGB")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("data/font.ttf", config["size"])
    except:
        font = ImageFont.load_default()

    safe_name = "".join(c for c in name if c.isalnum() or c in " _-")

    draw.text(
        (config["x"], config["y"]),
        safe_name,
        fill="black",
        font=font,
        anchor="mm"
    )

    file_path = f"data/{safe_name}_{cert_type}.png"
    img.save(file_path)

    return file_path

# 🚀 START
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer("👇 Avval kanallarga obuna bo‘ling:", reply_markup=keyboard())

# ✅ CHECK (INSTAGRAM BUTTONLAR BILAN)
@dp.callback_query_handler(lambda c: c.data == "check")
async def check(call: types.CallbackQuery):

    if await check_sub(call.from_user.id):

        kb = InlineKeyboardMarkup(row_width=1)

        for link in INSTAGRAM_LINKS:
            kb.add(InlineKeyboardButton("📸 Instagram sahifa", url=link))

        kb.add(InlineKeyboardButton("✅ Tasdiqlayman", callback_data="confirm"))

        await call.message.edit_text(
            "📸 Instagram sahifalarni ham ko‘rib chiqing:",
            reply_markup=kb
        )

    else:
        await call.answer("❌ Avval obuna bo‘ling!", show_alert=True)

# 🎉 CONFIRM → SERT TANLASH
@dp.callback_query_handler(lambda c: c.data == "confirm")
async def choose_cert(call: types.CallbackQuery):

    kb = InlineKeyboardMarkup(row_width=2)
    for i in range(1, 7):
        kb.insert(InlineKeyboardButton(f"{i}-sertifikat", callback_data=f"sert{i}"))

    await call.message.answer("📄 Sertifikatni tanlang:", reply_markup=kb)

# 🧾 TANLASH → ISM
@dp.callback_query_handler(lambda c: c.data.startswith("sert"))
async def ask_name(call: types.CallbackQuery, state: FSMContext):

    await Form.name.set()
    await call.message.answer("✍️ Ism va familiyangizni yozing:")

# ✍️ ISM → 6 TA SERT
@dp.message_handler(state=Form.name)
async def get_name(msg: types.Message, state: FSMContext):

    name = msg.text.strip()

    if len(name) < 5 or " " not in name:
        return await msg.answer("❗ Ism va familiya to‘liq yozilsin (Ali Valiyev)")

    name = name[:40]

    try:
        for cert_type in TEMPLATES.keys():
            cert = generate_certificate(name, cert_type)

            with open(cert, "rb") as photo:
                await bot.send_photo(
                    msg.from_user.id,
                    photo,
                    caption=f"🎉 {cert_type} tayyor!"
                )

    except Exception as e:
        await msg.answer(f"❗ Xato: {e}")

    await state.finish()

# 🖼️ ADMIN TEMPLATE YUKLASH
template_index = 1

@dp.message_handler(content_types=['photo'])
async def upload(msg: types.Message):
    global template_index

    if msg.from_user.id != ADMIN_ID:
        return

    os.makedirs("data", exist_ok=True)

    if template_index > 6:
        template_index = 1

    path = f"data/template{template_index}.png"

    await msg.photo[-1].download(destination_file=path)

    await msg.answer(f"✅ template{template_index} saqlandi")

    template_index += 1

# ▶️ RUN
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
