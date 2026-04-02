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
    "sert1": {  # 1-rasm (Yosh Ekologlar Tashakkurnoma)
        "file": f"{TEMPLATE_DIR}/sert1.png",
        "x": 650,      # markazga yaqin
        "y": 520,
        "size": 58,
        "color": (0, 0, 0)          # qora
    },
    "sert2": {  # 2-rasm (STEAM Academy Sertifikat)
        "file": f"{TEMPLATE_DIR}/sert2.png",
        "x": 700,
        "y": 520,
        "size": 52,
        "color": (0, 51, 102)       # quyuq ko'k
    },
    "sert3": {  # 3-rasm (OEP Sertifikat)
        "file": f"{TEMPLATE_DIR}/sert3.png",
        "x": 650,
        "y": 680,
        "size": 55,
        "color": (0, 80, 0)
    },
    "sert4": {  # 4-rasm (OEP Tashakkurnoma)
        "file": f"{TEMPLATE_DIR}/sert4.png",
        "x": 650,
        "y": 620,
        "size": 62,
        "color": (0, 100, 0)
    },
    "sert5": {  # 5-rasm (Toshkent Yosh Ekologlar)
        "file": f"{TEMPLATE_DIR}/sert5.png",
        "x": 650,
        "y": 720,
        "size": 60,
        "color": (0, 70, 0)
    },
    "sert6": {  # 6-rasm (Global Vibe Forum)
        "file": f"{TEMPLATE_DIR}/sert6.png",
        "x": 850,      # inglizcha sertifikat kengroq
        "y": 480,
        "size": 55,
        "color": (0, 0, 0)
    }
}

# ================== STATE ==================
class Form(StatesGroup):
    name = State()

# ================== SERTIFIKAT GENERATSIYA (YANGILANGAN) ==================
def generate_certificate(name: str, template_key: str) -> str:
    if template_key not in TEMPLATES:
        raise Exception(f"Template {template_key} topilmadi")

    config = TEMPLATES[template_key]
    img = Image.open(config["file"]).convert("RGB")
    draw = ImageDraw.Draw(img)

    safe_name = "".join(c for c in name if c.isalnum() or c in " -'")[:50]

    font_path = "data/font.ttf"   # Bu yerga yaxshi bold shrift qo'ying (Montserrat-Bold.ttf yoki Arial-Bold)
    font_size = config.get("size", 60)
    color = config.get("color", (0, 0, 0))

    # Shriftni yuklash (topilmasa default)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        logging.warning(f"Font topilmadi: {font_path}. Default ishlatilmoqda.")
        font = ImageFont.load_default()

    # Avtomatik shrift o'lchamini moslashtirish (juda uzun ism bo'lsa kichraytiradi)
    while font_size > 30:
        bbox = draw.textbbox((0, 0), safe_name, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width < img.size[0] - 200:   # chetidan 100px bo'sh joy
            break
        font_size -= 3
        font = ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else ImageFont.load_default()

    # Markazlashtirilgan yozish (anchor="mm")
    draw.text(
        (config["x"], config["y"]),
        safe_name,
        fill=color,
        font=font,
        anchor="mm"          # muhim! markazlashtirish
    )

    output_path = f"{CERT_DIR}/{safe_name.replace(' ', '_')}_{template_key}.jpg"
    img.save(output_path, optimize=True, quality=92)
    return output_path

# ================== ADMIN: TEMPLATE YUKLASH (o'zgarmadi) ==================
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
    except:
        await msg.answer("❌ Format: /setpos sert1 650 520 58")

# ================== QOLGAN KOD (o'zgarmadi) ==================
# ... (start, callback handlerlar, get_name va boshqalar o'zgarmay qoladi)

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
