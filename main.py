import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from PIL import Image, ImageDraw, ImageFont

# 🔐 TOKEN (qo‘lda yoz tavsiya)
BOT_TOKEN = "TOKENINGNI_BU_YERGA_YOZ"
ADMIN_ID = 5915034478

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

# 📂 TEMPLATE
TEMPLATES = {
    "sert1": {"file": "data/template1.png", "x": 750, "y": 430, "size": 60},
    "sert2": {"file": "data/template2.png", "x": 750, "y": 500, "size": 80},
    "sert3": {"file": "data/template3.png", "x": 750, "y": 480, "size": 75},
    "sert4": {"file": "data/template4.png", "x": 750, "y": 520, "size": 75},
    "sert5": {"file": "data/template5.png", "x": 750, "y": 500, "size": 70},
    "sert6": {"file": "data/template6.png", "x": 750, "y": 510, "size": 70},
}

# 🔘 START MENU
def keyboard():
    kb = InlineKeyboardMarkup(row_width=1)

    for ch in TELEGRAM_CHANNELS:
        kb.add(InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}"))

    kb.add(InlineKeyboardButton("📸 Instagram", callback_data="insta"))
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

# 🖼 SERTIFIKAT
def generate_certificate(name, cert_type):
    config = TEMPLATES[cert_type]

    if not os.path.exists(config["file"]):
        raise Exception(f"{cert_type} template topilmadi")

    os.makedirs("data", exist_ok=True)

    img = Image.open(config["file"]).convert("RGB")
    draw = ImageDraw.Draw(img)

    safe_name = "".join(c for c in name if c.isalnum() or c in " _-")

    size = config["size"]

    while size > 30:
        try:
            font = ImageFont.truetype("data/font.ttf", size)
        except:
            font = ImageFont.load_default()

        w, h = draw.textbbox((0, 0), safe_name, font=font)[2:]

        if w < img.size[0] - 200:
            break
        size -= 2

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
    await msg.answer("👇 Avval obuna bo‘ling:", reply_markup=keyboard())

# 📸 INSTAGRAM
@dp.callback_query_handler(lambda c: c.data == "insta")
async def show_insta(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)

    for link in INSTAGRAM_LINKS:
        kb.add(InlineKeyboardButton("📸 Instagram sahifa", url=link))

    kb.add(InlineKeyboardButton("✅ Tasdiqlayman", callback_data="confirm"))

    await call.message.answer("📸 Instagram sahifalarni ko‘ring:", reply_markup=kb)

# ✅ CHECK
@dp.callback_query_handler(lambda c: c.data == "check")
async def check(call: types.CallbackQuery):

    if await check_sub(call.from_user.id):

        kb = InlineKeyboardMarkup(row_width=1)

        for link in INSTAGRAM_LINKS:
            kb.add(InlineKeyboardButton("📸 Instagram sahifa", url=link))

        kb.add(InlineKeyboardButton("✅ Tasdiqlayman", callback_data="confirm"))

        await call.message.edit_text("📸 Instagramlarni ham ko‘rib chiqing:", reply_markup=kb)
    else:
        await call.answer("❌ Avval obuna bo‘ling!", show_alert=True)

# 🎉 CONFIRM
@dp.callback_query_handler(lambda c: c.data == "confirm")
async def ask_name(call: types.CallbackQuery):
    await Form.name.set()
    await call.message.answer("✍️ Ism va familiyangizni yozing:")

# ✍️ ISM
@dp.message_handler(state=Form.name)
async def get_name(msg: types.Message, state: FSMContext):

    name = msg.text.strip()

    if len(name) < 5 or " " not in name:
        return await msg.answer("❗ To‘liq ism yozing (Ali Valiyev)")

    name = name[:40]

    try:
        for cert_type in TEMPLATES.keys():
            cert = generate_certificate(name, cert_type)

            with open(cert, "rb") as photo:
                await bot.send_photo(msg.from_user.id, photo)

    except Exception as e:
        await msg.answer(f"❗ Xato: {e}")

    await state.finish()

# ▶️ RUN
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
