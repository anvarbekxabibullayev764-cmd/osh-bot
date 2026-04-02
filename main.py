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

BOT_TOKEN = "8736787100:AAGaJMulAr7bORxFP-J_pH2somGQPka17HE"   # ❗ eski tokenni almashtiring
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

TEMPLATES = {}

TEMPLATE_DIR = "data/templates"
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs("data/certificates", exist_ok=True)

class Form(StatesGroup):
    name = State()

def main_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    for ch in TELEGRAM_CHANNELS:
        kb.add(InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    kb.add(InlineKeyboardButton("📸 Instagram", callback_data="insta"))
    kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
    return kb

async def check_subscription(user_id: int) -> bool:
    for channel in TELEGRAM_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def generate_certificate(name: str, template_key: str) -> str:
    if template_key not in TEMPLATES:
        raise Exception(f"Template {template_key} topilmadi")

    config = TEMPLATES[template_key]
    img = Image.open(config["file"]).convert("RGB")
    draw = ImageDraw.Draw(img)

    safe_name = "".join(c for c in name if c.isalnum() or c in " _-")[:45]

    size = config.get("size", 70)
    font_path = "data/font.ttf"

    while size > 25:
        try:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, size)
            else:
                font = ImageFont.load_default()
                break
        except:
            font = ImageFont.load_default()
            break

        bbox = draw.textbbox((0, 0), safe_name, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width < img.size[0] - 180:
            break
        size -= 2

    draw.text(
        (config["x"], config["y"]),
        safe_name,
        fill="black",
        font=font,
        anchor="mm"
    )

    output_path = f"data/certificates/{safe_name}_{template_key}.jpg"
    img.save(output_path, "JPEG", quality=95)
    return output_path

@dp.message_handler(commands=['addtemplate'], user_id=ADMIN_ID)
async def add_template(msg: types.Message):
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await msg.answer("❌ Iltimos, rasmga reply qilib /addtemplate yozing.")
        return

    template_num = len(TEMPLATES) + 1
    template_key = f"sert{template_num}"

    photo = msg.reply_to_message.photo[-1]
    file_path = f"{TEMPLATE_DIR}/{template_key}.png"

    await photo.download(destination_file=file_path)

    TEMPLATES[template_key] = {
        "file": file_path,
        "x": 750,
        "y": 480,
        "size": 70
    }

    await msg.answer(f"✅ {template_key} qo‘shildi!")

@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer("👋 Salom!", reply_markup=main_keyboard())

@dp.callback_query_handler(lambda c: c.data == "confirm")
async def ask_name(call: types.CallbackQuery):
    await Form.name.set()
    await call.message.answer("Ism familiya yozing:")
    await call.answer()

@dp.message_handler(state=Form.name)
async def get_name(msg: types.Message, state: FSMContext):
    name = msg.text.strip()
    await msg.answer("⏳ Tayyorlanmoqda...")

    sent_count = 0
    for template_key in sorted(TEMPLATES.keys()):
        try:
            cert_path = generate_certificate(name, template_key)
            with open(cert_path, "rb") as photo:
                await bot.send_photo(msg.from_user.id, photo)
            sent_count += 1
        except Exception as e:
            logging.error(e)

    await msg.answer(f"✅ {sent_count} ta sertifikat yuborildi")
    await state.finish()

if __name__ == "__main__":
    for file in os.listdir(TEMPLATE_DIR):
        if file.endswith((".png", ".jpg", ".jpeg")):   # 🔥 ASOSIY TUZATISH
            key = file.rsplit(".", 1)[0]
            TEMPLATES[key] = {
                "file": os.path.join(TEMPLATE_DIR, file),
                "x": 750,
                "y": 480,
                "size": 70
            }
            print(f"Loaded template: {key}")

    if not TEMPLATES:
        print("❌ TEMPLATE YO‘Q")

    executor.start_polling(dp, skip_updates=True)
