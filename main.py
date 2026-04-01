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

BOT_TOKEN = "8736787100:AAGaJMulAr7bORxFP-J_pH2somGQPka17HE"   # ← O'zgartiring!
ADMIN_ID = 5915034478

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ================== SOZLAMALAR ==================
TELEGRAM_CHANNELS = ["@xdp_shayxontohur", "@olimmov_ozodbekk"]

INSTAGRAM_LINKS = [
    "https://www.instagram.com/o.o.olimmov",
    "https://www.instagram.com/xdp.shayxontohur",
    "https://www.instagram.com/anvarbek.xabibullayev"
]

# Yangi: Admin tomonidan yuklangan 6 ta template
TEMPLATES = {}   # { "sert1": {"file": "path", "x": 750, "y": 430, "size": 60}, ... }

TEMPLATE_DIR = "data/templates"
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs("data/certificates", exist_ok=True)

# ================== STATE ==================
class Form(StatesGroup):
    name = State()

# ================== KEYBOARD ==================
def main_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    for ch in TELEGRAM_CHANNELS:
        kb.add(InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    kb.add(InlineKeyboardButton("📸 Instagram", callback_data="insta"))
    kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
    return kb

# ================== OBUNA TEKSHIRISH ==================
async def check_subscription(user_id: int) -> bool:
    for channel in TELEGRAM_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ================== SERTIFIKAT GENERATSIYA ==================
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
            font = ImageFont.truetype(font_path, size)
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

    output_path = f"data/certificates/{safe_name}_{template_key}.png"
    img.save(output_path, optimize=True, quality=95)
    return output_path

# ================== ADMIN: TEMPLATE YUKLASH ==================
@dp.message_handler(commands=['addtemplate'], user_id=ADMIN_ID)
async def add_template(msg: types.Message):
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await msg.answer("❌ Iltimos, sertifikat rasmini yuborib, unga /addtemplate deb reply qiling.")
        return

    # Yangi template nomi (sert1, sert2 ...)
    template_num = len(TEMPLATES) + 1
    template_key = f"sert{template_num}"

    photo = msg.reply_to_message.photo[-1]
    file_path = f"{TEMPLATE_DIR}/{template_key}.png"

    await photo.download(destination_file=file_path)

    # Default qiymatlar (keyin o'zgartirsa bo'ladi)
    TEMPLATES[template_key] = {
        "file": file_path,
        "x": 750,
        "y": 480,
        "size": 70
    }

    await msg.answer(f"✅ {template_key} muvaffaqiyatli qo‘shildi!\n\n"
                     f"Koordinatalarni o‘zgartirish uchun:\n"
                     f"`/setpos {template_key} x y size`\n"
                     f"Masalan: `/setpos sert1 750 430 65`")

# ================== ADMIN: POZITSIYA O'ZGARTIRISH ==================
@dp.message_handler(commands=['setpos'], user_id=ADMIN_ID)
async def set_position(msg: types.Message):
    try:
        _, template_key, x, y, size = msg.text.split()
        x, y, size = int(x), int(y), int(size)

        if template_key not in TEMPLATES:
            await msg.answer("❌ Bunday template yo‘q!")
            return

        TEMPLATES[template_key].update({"x": x, "y": y, "size": size})
        await msg.answer(f"✅ {template_key} yangilandi:\nX: {x} | Y: {y} | Size: {size}")
    except:
        await msg.answer("❌ Format xato!\nTo‘g‘ri: `/setpos sert1 750 430 65`")

# ================== START ==================
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer("👋 Salom! Sertifikat olish uchun avval quyidagilarni bajaring:", 
                     reply_markup=main_keyboard())

# ================== CALLBACK HANDLERLAR ==================
@dp.callback_query_handler(lambda c: c.data == "insta")
async def show_insta(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)
    for link in INSTAGRAM_LINKS:
        kb.add(InlineKeyboardButton("📸 Instagram sahifa", url=link))
    kb.add(InlineKeyboardButton("✅ Tasdiqlayman", callback_data="confirm"))

    await call.message.answer("📸 Instagram sahifalarni ko‘rib chiqing:", reply_markup=kb)
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == "check")
async def check_sub_handler(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        kb = InlineKeyboardMarkup(row_width=1)
        for link in INSTAGRAM_LINKS:
            kb.add(InlineKeyboardButton("📸 Instagram sahifa", url=link))
        kb.add(InlineKeyboardButton("✅ Tasdiqlayman", callback_data="confirm"))

        await call.message.edit_text("✅ Kanallarga obuna bo‘ldingiz!\nEndi Instagramlarni ham ko‘rib chiqing:", 
                                     reply_markup=kb)
    else:
        await call.answer("❌ Avval barcha kanallarga obuna bo‘ling!", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "confirm")
async def ask_name(call: types.CallbackQuery):
    await Form.name.set()
    await call.message.answer("✍️ Ism va familiyangizni to‘liq yozing:\nMasalan: Anvarbek Xabibullayev")
    await call.answer()

# ================== ISM QABUL QILISH VA SERTIFIKAT BERISH ==================
@dp.message_handler(state=Form.name)
async def get_name(msg: types.Message, state: FSMContext):
    name = msg.text.strip()
    if len(name) < 5 or " " not in name:
        await msg.answer("❗ Iltimos, ism va familiyani to‘liq yozing (masalan: Ali Valiyev)")
        return

    name = name[:45]
    await msg.answer("🎉 Sertifikatlaringiz tayyorlanmoqda... Biroz kuting.")

    sent_count = 0
    for template_key in sorted(TEMPLATES.keys()):
        try:
            cert_path = generate_certificate(name, template_key)
            with open(cert_path, "rb") as photo:
                await bot.send_photo(
                    msg.from_user.id,
                    photo,
                    caption=f"📜 {template_key.upper()} - Sertifikat"
                )
            sent_count += 1
        except Exception as e:
            logging.error(f"Error generating {template_key}: {e}")
            await msg.answer(f"❌ {template_key} da xatolik: {str(e)[:100]}")

    await msg.answer(f"✅ Barcha {sent_count} ta sertifikat muvaffaqiyatli yuborildi!")
    await state.finish()

# ================== BOTNI ISHGA TUSHIRISH ==================
if __name__ == "__main__":
    # Mavjud template'larni yuklash
    for file in os.listdir(TEMPLATE_DIR):
        if file.endswith(".png"):
            key = file.replace(".png", "")
            TEMPLATES[key] = {
                "file": os.path.join(TEMPLATE_DIR, file),
                "x": 750,
                "y": 480,
                "size": 70
            }
            print(f"Loaded template: {key}")

    if not TEMPLATES:
        print("⚠️ Hozircha hech qanday template yuklanmagan. Admin /addtemplate bilan qo'shsin.")

    executor.start_polling(
        dp,
        skip_updates=True,
        allowed_updates=["message", "callback_query"]
    )
