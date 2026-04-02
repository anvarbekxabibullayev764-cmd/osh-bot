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
    "sert1": {  # Yosh Ekologlar Tashakkurnoma
        "file": f"{TEMPLATE_DIR}/sert1.png",
        "x": 380,
        "y": 560,
        "size": 70,
        "color": (0, 0, 0)
    },
    "sert2": {  # STEAM Academy Sertifikat
        "file": f"{TEMPLATE_DIR}/sert2.png",
        "x": 420,
        "y": 520,
        "size": 70,
        "color": (0, 51, 102)
    },
    "sert3": {  # OEP Sertifikat
        "file": f"{TEMPLATE_DIR}/sert3.png",
        "x": 350,
        "y": 560,
        "size": 70,
        "color": (0, 80, 0)
    },
    "sert4": {  # OEP Tashakkurnoma
        "file": f"{TEMPLATE_DIR}/sert4.png",
        "x": 420,
        "y": 520,
        "size": 70,
        "color": (0, 100, 0)
    },
    "sert5": {  # Toshkent Yosh Ekologlar
        "file": f"{TEMPLATE_DIR}/sert5.png",
        "x": 420,
        "y": 520,
        "size": 60,
        "color": (0, 70, 0)
    },
    "sert6": {  # Global Vibe Forum
        "file": f"{TEMPLATE_DIR}/sert6.png",
        "x": 400,
        "y": 330,
        "size": 55,
        "color": (0, 0, 0)
    }
}

# ================== STATE ==================
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

    font_path = "data/font.ttf"   # Bu yerga o'zingizning shriftingizni qo'ying
    font_size = config.get("size", 60)
    color = config.get("color", (0, 0, 0))

    # Shriftni yuklash
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        logging.warning(f"Font topilmadi: {font_path}. Default ishlatilmoqda.")
        font = ImageFont.load_default()

    # Avtomatik shrift o'lchamini moslashtirish
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

    # Matnni markazlashtirib yozish
    draw.text(
        (config["x"], config["y"]),
        safe_name,
        fill=color,
        font=font,
        anchor="mm"
    )

    output_path = f"{CERT_DIR}/{safe_name.replace(' ', '*')}*{template_key}.jpg"
    img.save(output_path, optimize=True, quality=92)
    return output_path


# ================== ADMIN: TEMPLATE QO'SHISH ==================
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


# ================== POSITION O'ZGARTIRISH ==================
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
    except Exception:
        await msg.answer("❌ Format: /setpos sert1 650 520 58")


# ================== QOLGAN KOD (start, handlerlar va h.k.) ==================
# Bu yerda sizning oldingi start, callback, get_name va boshqa handlerlaringiz qoladi.
# Agar ularni yuborsangiz, to‘liq qo‘shib beraman.


# ================== BOTNI ISHGA TUSHIRISH ==================
if __name__ == "__main__":
    # Mavjud template larni avtomatik yuklash
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
