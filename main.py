import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from PIL import Image, ImageDraw, ImageFont

# 🔐 ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5915034478

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# 📡 Kanallar
TELEGRAM_CHANNELS = [
    "@xdp_shayxontohur",
    "@olimmov_ozodbekk"
]

INSTAGRAM_LINKS = [
    "https://www.instagram.com/o.o.olimmov",
    "https://www.instagram.com/xdp.shayxontohur",
    "https://www.instagram.com/anvarbek.xabibullayev"
]


# 🔘 Keyboard
def keyboard():
    kb = InlineKeyboardMarkup(row_width=1)

    for ch in TELEGRAM_CHANNELS:
        kb.add(InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch[1:]}"))

    for link in INSTAGRAM_LINKS:
        kb.add(InlineKeyboardButton("📸 Instagram", url=link))

    kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
    return kb


# 🔍 Tekshiruv
async def check_sub(user_id):
    for ch in TELEGRAM_CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
except Exception as e:
    print(e)
    return False
    return True


# 🖼️ Sertifikat yaratish
def generate_certificate(name):
    os.makedirs("data", exist_ok=True)

    template = "data/template.png"

    if not os.path.exists(template):
        raise Exception("❗ Admin hali rasm yuklamagan")

    img = Image.open(template)
    draw = ImageDraw.Draw(img)

    font = ImageFont.load_default()

    w, h = img.size
    bbox = draw.textbbox((0, 0), name, font=font)
    text_w = bbox[2] - bbox[0]

    position = ((w - text_w) // 2, h // 2)

    draw.text(position, name, fill="black", font=font)

    file = f"data/{name}.png"
    img.save(file)

    return file


# 🚀 Start
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer("👇 Obuna bo‘ling:", reply_markup=keyboard())


# ✅ Tekshirish
@dp.callback_query_handler(lambda c: c.data == "check")
async def check(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Tasdiqlayman", callback_data="confirm")
        )
        await call.message.answer("Instagramga ham obuna bo‘ldingizmi?", reply_markup=kb)
    else:
        await call.answer("❌ Avval Telegram va instagramga obuna bo‘ling!", show_alert=True)


# 🎉 Sertifikat
@dp.callback_query_handler(lambda c: c.data == "confirm")
async def confirm(call: types.CallbackQuery):
    try:
        cert = generate_certificate(call.from_user.full_name)

        await bot.send_photo(
            call.from_user.id,
            photo=open(cert, "rb"),
            caption="🎉 Sertifikat berildi!"
        )
    except Exception as e:
        await call.message.answer(str(e))


# 🖼️ Admin rasm yuklaydi
@dp.message_handler(content_types=['photo'])
async def upload(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    os.makedirs("data", exist_ok=True)

    photo = msg.photo[-1]
    await photo.download(destination_file="data/template.png")

    await msg.answer("✅ Rasm saqlandi!")


# ▶️ Run
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
