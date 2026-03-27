import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from PIL import Image, ImageDraw, ImageFont

# 🔐 ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5915034478

if not BOT_TOKEN:
    raise Exception("❌ BOT_TOKEN topilmadi (env sozlanmagan)")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# 📡 Kanallar (USERNAME yoki ID ishlatish mumkin)
TELEGRAM_CHANNELS = [
    "@xdp_shayxontohur",
    "@olimmov_ozodbekk"
]

# 📸 Instagram (faqat link)
INSTAGRAM_LINKS = [
    "https://www.instagram.com/o.o.olimmov",
    "https://www.instagram.com/xdp.shayxontohur",
    "https://www.instagram.com/anvarbek.xabibullayev"
]


# 🔘 Keyboard
def keyboard():
    kb = InlineKeyboardMarkup(row_width=1)

    for ch in TELEGRAM_CHANNELS:
        kb.add(
            InlineKeyboardButton(
                text=f"📢 {ch}",
                url=f"https://t.me/{ch.replace('@','')}"
            )
        )

    for link in INSTAGRAM_LINKS:
        kb.add(
            InlineKeyboardButton("📸 Instagram", url=link)
        )

    kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
    return kb


# 🔍 OBUNA TEKSHIRISH (FIXED)
async def check_sub(user_id: int):
    for ch in TELEGRAM_CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            status = member.status

            if status not in ["member", "administrator", "creator"]:
                return False

        except Exception as e:
            logging.error(f"Channel error {ch}: {e}")
            return False

    return True


# 🖼️ SERTIFIKAT YARATISH (FIXED)
def generate_certificate(name: str):
    os.makedirs("data", exist_ok=True)

    template = "data/template.png"

    if not os.path.exists(template):
        raise Exception("❗ Template rasm topilmadi (admin yuklamagan)")

    img = Image.open(template).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = ImageFont.load_default()

    # safe name (file error oldini olish)
    safe_name = "".join(c for c in name if c.isalnum() or c in " _-")

    w, h = img.size

    bbox = draw.textbbox((0, 0), safe_name, font=font)
    text_w = bbox[2] - bbox[0]

    position = ((w - text_w) // 2, h // 2)

    draw.text(position, safe_name, fill="black", font=font)

    file_path = f"data/{safe_name}.png"
    img.save(file_path)

    return file_path


# 🚀 START
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer(
        "👇 Sertifikat olish uchun kanallarga obuna bo‘ling:",
        reply_markup=keyboard()
    )


# ✅ CHECK
@dp.callback_query_handler(lambda c: c.data == "check")
async def check(call: types.CallbackQuery):

    if await check_sub(call.from_user.id):

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Tasdiqlayman", callback_data="confirm")
        )

        await call.message.edit_text(
            "📸 Instagramga ham kirgan bo‘lsangiz tasdiqlang:",
            reply_markup=kb
        )

    else:
        await call.answer(
            "❌ Avval barcha Telegram kanallarga obuna bo‘ling!",
            show_alert=True
        )


# 🎉 CONFIRM
@dp.callback_query_handler(lambda c: c.data == "confirm")
async def confirm(call: types.CallbackQuery):
    try:
        cert = generate_certificate(call.from_user.full_name)

        with open(cert, "rb") as photo:
            await bot.send_photo(
                call.from_user.id,
                photo=photo,
                caption="🎉 Sertifikat tayyor!"
            )

    except Exception as e:
        await call.message.answer(f"❗ Xato: {e}")


# 🖼️ ADMIN UPLOAD TEMPLATE
@dp.message_handler(content_types=['photo'])
async def upload(msg: types.Message):

    if msg.from_user.id != ADMIN_ID:
        return

    os.makedirs("data", exist_ok=True)

    photo = msg.photo[-1]
    await photo.download(destination_file="data/template.png")

    await msg.answer("✅ Template saqlandi!")


# ▶️ RUN
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
