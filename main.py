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

BOT_TOKEN = "8736787100:AAGaJMulAr7bORxFP-J_pH2somGQPka17HE"  # ← O'zgartiring!
ADMIN_ID = 5915034478

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ================== SOZLAMALAR ==================
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

# ================== TEMPLATES (faqat 6 ta) ==================
TEMPLATES = {
    "sert1": {"file": f"{TEMPLATE_DIR}/sert1.png", "x": 650, "y": 520, "size": 58, "color": (0, 0, 0)},
    "sert2": {"file": f"{TEMPLATE_DIR}/sert2.png", "x": 700, "y": 520, "size": 52, "color": (0, 51, 102)},
    "sert3": {"file": f"{TEMPLATE_DIR}/sert3.png", "x": 650, "y": 680, "size": 55, "color": (0, 80, 0)},
    "sert4": {"file": f"{TEMPLATE_DIR}/sert4.png", "x": 650, "y": 620, "size": 62, "color": (0, 100, 0)},
    "sert5": {"file": f"{TEMPLATE_DIR}/sert5.png", "x": 650, "y": 720, "size": 60, "color": (0, 70, 0)},
    "sert6": {"file": f"{TEMPLATE_DIR}/sert6.png", "x": 850, "y": 480, "size": 55, "color": (0, 0, 0)},
}

class Form(StatesGroup):
    name = State()

# ================== SERTIFIKAT GENERATSIYA ==================
def generate_certificate(name: str, template_key: str) -> str:
    if template_key not in TEMPLATES:
        raise Exception(f"Template {template_key} topilmadi")

    config = TEMPLATES[template_key]
    img = Image.open(config["file"]).convert("RGB")
    draw = ImageDraw.Draw(img)

    safe_name = "".join(c for c in name if c.isalnum() or c in " -'")[:50]
    font_path = "data/font.ttf"

    font_size = config.get("size", 60)
    color = config.get("color", (0, 0, 0))

    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        logging.warning(f"Font topilmadi: {font_path}. Default ishlatilmoqda.")
        font = ImageFont.load_default()

    while font_size > 30:
        bbox = draw.textbbox((0, 0), safe_name, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width < img.size[0] - 200:
            break
        font_size -= 3
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()

    draw.text((config["x"], config["y"]), safe_name, fill=color, font=font, anchor="mm")

    output_path = f"{CERT_DIR}/{safe_name.replace(' ', '_')}_{template_key}.jpg"
    img.save(output_path, optimize=True, quality=92)
    return output_path


# ================== OBUna TEKSHIRISH ==================
async def check_subscription(user_id: int) -> bool:
    for channel in TELEGRAM_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True


# ================== START ==================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    if not await check_subscription(message.from_user.id):
        kb = InlineKeyboardMarkup(row_width=1)
        for ch in TELEGRAM_CHANNELS:
            kb.add(InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch[1:]}"))
        
        for link in INSTAGRAM_LINKS:
            kb.add(InlineKeyboardButton("📸 Instagram", url=link))
        
        kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))

        await message.answer("📢 **Obuna bo‘ling:**", reply_markup=kb)
        return

    # Obuna tasdiqlangan bo'lsa — ism so'raydi
    await message.answer("✍️ Iltimos, to‘liq ismingizni kiriting:")
    await Form.name.set()


# ================== TEKSHIRISH TUGMASI ==================
@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_sub_callback(callback: types.CallbackQuery, state: FSMContext):
    if await check_subscription(callback.from_user.id):
        await callback.message.edit_text("✅ Obuna tasdiqlandi!\n\n✍️ Endi to‘liq ismingizni kiriting:")
        await Form.name.set()
    else:
        await callback.answer("❌ Hali ham barcha kanallarga obuna bo‘lmadingiz!", show_alert=True)
    await callback.answer()


# ================== ISM QABUL QILISH VA 6 TA SERTIFIKAT YUBORISH ==================
@dp.message_handler(state=Form.name)
async def get_name(message: types.Message, state: FSMContext):
    name = message.text.strip()

    await message.answer(f"⏳ {name} uchun 6 ta sertifikat tayyorlanmoqda...\nBiroz kuting...")

    success_count = 0
    for template_key in ["sert1", "sert2", "sert3", "sert4", "sert5", "sert6"]:
        try:
            cert_path = generate_certificate(name, template_key)
            
            with open(cert_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photo,
                    caption=f"✅ Sertifikat tayyor!\n"
                            f"👤 Ism: <b>{name}</b>\n"
                            f"📜 Tur: {template_key}"
                )
            success_count += 1
        except Exception as e:
            logging.error(f"{template_key} da xatolik: {e}")
            await message.answer(f"❌ {template_key} yaratishda xatolik yuz berdi.")

    await message.answer(f"🎉 Hammasi tugadi! Jami {success_count} ta sertifikat yuborildi.")
    await state.finish()


# ================== ADMIN BUYRUQLARI (o'zgarmadi) ==================
@dp.message_handler(commands=['addtemplate'], user_id=ADMIN_ID)
async def add_template(msg: types.Message):
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await msg.answer("❌ Sertifikat rasmini yuborib, /addtemplate ga reply qiling.")
        return
    # ... sizning eski kodingizdagi qolgan qismi


@dp.message_handler(commands=['setpos'], user_id=ADMIN_ID)
async def set_position(msg: types.Message):
    try:
        _, key, x, y, size = msg.text.split()
        x, y, size = int(x), int(y), int(size)
        if key not in TEMPLATES:
            await msg.answer("❌ Bunday template yo‘q!")
            return
        TEMPLATES[key].update({"x": x, "y": y, "size": size})
        await msg.answer(f"✅ {key} yangilandi:\nX: {x} | Y: {y} | Size: {size}")
    except:
        await msg.answer("❌ Format: /setpos sert1 650 520 58")


# ================== BOTNI ISHGA TUSHIRISH ==================
if __name__ == "__main__":
    print("✅ Bot ishga tushdi! Obuna bo‘lgandan keyin 6 ta sertifikat avtomatik yuboriladi.")
    executor.start_polling(dp, skip_updates=True)
