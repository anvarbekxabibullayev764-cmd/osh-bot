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

# ================== HAR BIR TEMPLATE UCHUN ANIQ SOZLAMALAR ==================
TEMPLATES = {
    "sert1": {"file": f"{TEMPLATE_DIR}/sert1.png", "x": 650, "y": 520, "size": 58, "color": (0, 0, 0)},
    "sert2": {"file": f"{TEMPLATE_DIR}/sert2.png", "x": 700, "y": 520, "size": 52, "color": (0, 51, 102)},
    "sert3": {"file": f"{TEMPLATE_DIR}/sert3.png", "x": 650, "y": 680, "size": 55, "color": (0, 80, 0)},
    "sert4": {"file": f"{TEMPLATE_DIR}/sert4.png", "x": 650, "y": 620, "size": 62, "color": (0, 100, 0)},
    "sert5": {"file": f"{TEMPLATE_DIR}/sert5.png", "x": 650, "y": 720, "size": 60, "color": (0, 70, 0)},
    "sert6": {"file": f"{TEMPLATE_DIR}/sert6.png", "x": 850, "y": 480, "size": 55, "color": (0, 0, 0)},
}

# ================== STATE ==================
class Form(StatesGroup):
    name = State()
    template_key = State()   # Tanlangan sertifikatni saqlash uchun

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
        keyboard = InlineKeyboardMarkup(row_width=1)
        for ch in TELEGRAM_CHANNELS:
            keyboard.add(InlineKeyboardButton("📢 Obuna bo‘lish", url=f"https://t.me/{ch[1:]}"))
        
        await message.answer(
            "❗ Botdan foydalanish uchun avval quyidagi kanallarga obuna bo‘ling:",
            reply_markup=keyboard
        )
        return

    # Obuna bo‘lgan bo‘lsa — sertifikat tanlash chiqadi
    kb = InlineKeyboardMarkup(row_width=2)
    for key in TEMPLATES.keys():
        num = key.replace("sert", "")
        kb.add(InlineKeyboardButton(f"🏆 Sertifikat {num}", callback_data=f"cert_{key}"))

    await message.answer(
        "👋 Salom!\n\n"
        "Qaysi sertifikatni olishni xohlaysiz?\n"
        "Pastdagi tugmalardan birini tanlang:",
        reply_markup=kb
    )


# ================== SERTIFIKAT TANLASH (CALLBACK) ==================
@dp.callback_query_handler(lambda c: c.data.startswith("cert_"))
async def process_cert_choice(callback: types.CallbackQuery, state: FSMContext):
    template_key = callback.data.replace("cert_", "")

    await state.update_data(template_key=template_key)
    await Form.name.set()

    await callback.message.edit_text(
        "✍️ Iltimos, to‘liq ismingizni kiriting:\n"
        "(Masalan: Anvarbek Xabibullayev)"
    )
    await callback.answer()


# ================== ISM QABUL QILISH ==================
@dp.message_handler(state=Form.name)
async def get_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    template_key = data.get("template_key")

    if not template_key:
        await message.answer("❌ Xatolik yuz berdi. Qaytadan /start bosing.")
        await state.finish()
        return

    name = message.text.strip()

    try:
        await message.answer("⏳ Sertifikatingiz tayyorlanmoqda, biroz kuting...")

        cert_path = generate_certificate(name, template_key)

        with open(cert_path, "rb") as photo:
            await bot.send_photo(
                message.chat.id,
                photo,
                caption=f"✅ Sertifikat tayyor!\n\n"
                        f"👤 Ism: <b>{name}</b>\n"
                        f"📜 Sertifikat turi: {template_key}"
            )
    except Exception as e:
        logging.error(f"Sertifikat xatosi: {e}")
        await message.answer("❌ Sertifikat yaratishda xatolik yuz berdi. Keyinroq urinib ko‘ring.")
    finally:
        await state.finish()


# ================== ADMIN BUYRUQLARI (sizning asl kodingiz) ==================
@dp.message_handler(commands=['addtemplate'], user_id=ADMIN_ID)
async def add_template(msg: types.Message):
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await msg.answer("❌ Sertifikat rasmini yuborib, /addtemplate ga reply qiling.")
        return

    template_num = len(TEMPLATES) + 1
    template_key = f"sert{template_num}"
    photo = msg.reply_to_message.photo[-1]
    file_path = f"{TEMPLATE_DIR}/{template_key}.png"

    await photo.download(destination_file=file_path)

    TEMPLATES[template_key] = {
        "file": file_path,
        "x": 650,
        "y": 550,
        "size": 60,
        "color": (0, 0, 0)
    }

    await msg.answer(f"✅ {template_key} qo‘shildi!\n"
                     f"Position o‘zgartirish: /setpos {template_key} x y size\n"
                     f"Masalan: /setpos {template_key} 650 520 58")


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
    for file in os.listdir(TEMPLATE_DIR):
        if file.endswith((".png", ".jpg", ".jpeg")):
            key = file.split('.')[0]
            if key not in TEMPLATES:
                TEMPLATES[key] = {
                    "file": os.path.join(TEMPLATE_DIR, file),
                    "x": 650,
                    "y": 550,
                    "size": 60,
                    "color": (0, 0, 0)
                }
                print(f"✅ Avtomatik yuklandi: {key}")

    if not TEMPLATES:
        print("⚠️ Hech qanday template topilmadi. Admin /addtemplate bilan qo'shsin.")

    executor.start_polling(dp, skip_updates=True)
