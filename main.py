import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8736787100:AAGaJMulAr7bORxFP-J_pH2somGQPka17HE"
ADMIN_ID = 5915034478

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

TELEGRAM_CHANNELS = ["@xdp_shayxontohur", "@olimmov_ozodbekk"]
INSTAGRAM_LINKS = [
    "https://www.instagram.com/anvarbek.xabibullayev",
    "https://www.instagram.com/o.o.olimmov",
    "https://www.instagram.com/xdp.shayxontohur"
]

TEMPLATE_DIR = "data/templates"
CERT_DIR = "data/certificates"

os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)

TEMPLATES = {
    "template1": {"file": f"{TEMPLATE_DIR}/template1.png", "x": 350, "y": 530, "size": 160, "color": (0, 0, 0)},
    "template2": {"file": f"{TEMPLATE_DIR}/template2.png", "x": 400, "y": 315, "size": 150, "color": (0, 51, 102)},
    "template3": {"file": f"{TEMPLATE_DIR}/template3.png", "x": 310, "y": 468, "size": 170, "color": (0, 80, 0)},
    "template4": {"file": f"{TEMPLATE_DIR}/template4.png", "x": 420, "y": 343, "size": 160, "color": (0, 100, 0)},
    "template5": {"file": f"{TEMPLATE_DIR}/template5.png", "x": 455, "y": 420, "size": 160, "color": (0, 70, 0)},
    "template6": {"file": f"{TEMPLATE_DIR}/template6.png", "x": 400, "y": 340, "size": 160, "color": (0, 0, 0)},
}

class Form(StatesGroup):
    name = State()

# ================== SERTIFIKAT ==================
def generate_certificate(name: str, template_key: str) -> str:
    config = TEMPLATES[template_key]
    img = Image.open(config["file"]).convert("RGB")
    draw = ImageDraw.Draw(img)

    safe_name = "".join(c for c in name if c.isalnum() or c in " -'")[:50]

    font_path = "data/font.ttf"
    font_size = config["size"]
    color = config["color"]

    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    max_width = img.size[0] - 120

    while font_size > 50:
        bbox = draw.textbbox((0, 0), safe_name, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            break
        font_size -= 8
        font = ImageFont.truetype(font_path, font_size)

    draw.text((config["x"], config["y"]), safe_name, fill=color, font=font, anchor="mm")

    output_path = f"{CERT_DIR}/{safe_name.replace(' ', '_')}_{template_key}.jpg"
    img.save(output_path, optimize=True, quality=92)

    return output_path

# ================== OBUNA TEKSHIRISH ==================
async def check_telegram_subscription(user_id: int) -> bool:
    for channel in TELEGRAM_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# ================== START ==================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if not await check_telegram_subscription(message.from_user.id):
        kb = InlineKeyboardMarkup(row_width=1)
        for ch in TELEGRAM_CHANNELS:
            kb.add(InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch[1:]}"))
        for link in INSTAGRAM_LINKS:
            kb.add(InlineKeyboardButton("📸 Instagram", url=link))
        kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))

        await message.answer("📢 Avval obuna bo‘ling:", reply_markup=kb)
        return

    kb = InlineKeyboardMarkup(row_width=1)
    for link in INSTAGRAM_LINKS:
        kb.add(InlineKeyboardButton("📸 Instagram", url=link))
    kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_instagram"))

    await message.answer("✅ Telegram OK\nEndi Instagram:", reply_markup=kb)

# ================== TEKSHIRISH ==================
@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_sub(callback: types.CallbackQuery):
    if await check_telegram_subscription(callback.from_user.id):
        kb = InlineKeyboardMarkup(row_width=1)
        for link in INSTAGRAM_LINKS:
            kb.add(InlineKeyboardButton("📸 Instagram", url=link))
        kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_instagram"))

        await callback.message.edit_text("✅ Telegram OK\nEndi Instagram:", reply_markup=kb)
    else:
        await callback.answer("❌ Obuna bo‘lmadingiz!", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "check_instagram")
async def check_instagram(callback: types.CallbackQuery):
    await callback.message.edit_text("✍️ Ismingizni kiriting:")
    await Form.name.set()

# ================== 12 TA SERTIFIKAT ==================
@dp.message_handler(state=Form.name)
async def get_name(message: types.Message, state: FSMContext):
    name = message.text.strip()

    await message.answer("⏳ 12 ta sertifikat tayyorlanmoqda...")

    success = 0
    failed = []

    for key in TEMPLATES.keys():
        try:
            # 1️⃣ Ism bilan
            cert = generate_certificate(name, key)
            with open(cert, "rb") as photo:
                await bot.send_photo(message.chat.id, photo, caption=f"✅ {key} (ism bilan)")
            success += 1

            # 2️⃣ Oddiy
            with open(TEMPLATES[key]["file"], "rb") as photo:
                await bot.send_photo(message.chat.id, photo, caption=f"🖼 {key} (oddiy)")
            success += 1

        except Exception as e:
            failed.append(key)

    text = f"🎉 Tugadi!\n📤 {success} ta yuborildi"

    if failed:
        text += "\n❌ Xatolik:\n"
        for f in failed:
            text += f"• {f}\n"

    await message.answer(text)
    await state.finish()

# ================== RUN ==================
if __name__ == "__main__":
    print("✅ Bot ishga tushdi!")
    executor.start_polling(dp, skip_updates=True)
