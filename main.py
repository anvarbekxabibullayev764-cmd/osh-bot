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

# ================== SERTIFIKAT GENERATSIYA ==================
def generate_certificate(name: str, template_key: str) -> str:
    try:
        config = TEMPLATES[template_key]
        img = Image.open(config["file"]).convert("RGB")
        draw = ImageDraw.Draw(img)

        safe_name = "".join(c for c in name if c.isalnum() or c in " -'")[:50]
        
        font_path = "data/font.ttf"
        font_size = config.get("size", 60)      # Bu yerda sizning kattaligingiz
        color = config.get("color", (0, 0, 0))

        # Yangi qism — bu yerda size avtomatik kichraymaydi
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()

        # Faqat juda uzun bo'lsa kichraytiradi
        max_width = img.size[0] - 20

font_path = "data/font.ttf"
font_size = config.get("size", 160)   # KATTA QILING (masalan 160–200)
color = config.get("color", (0, 0, 0))

try:
    font = ImageFont.truetype(font_path, font_size)
except:
    font = ImageFont.load_default()

# MATNNI MARKAZGA TO‘G‘RILASH
bbox = draw.textbbox((0, 0), safe_name, font=font)
text_width = bbox[2] - bbox[0]

x = config["x"]
y = config["y"]

# Agar markaz bo‘lsa:
draw.text((x, y), safe_name, fill=color, font=font, anchor="mm")
        # Yozuvni chizish
        draw.text((config["x"], config["y"]), safe_name, fill=color, font=font, anchor="mm")

        output_path = f"{CERT_DIR}/{safe_name.replace(' ', '_')}_{template_key}.jpg"
        img.save(output_path, optimize=True, quality=92)
        return output_path

    except Exception as e:
        logging.error(f"{template_key} xatosi: {e}")
        raise

async def check_telegram_subscription(user_id: int) -> bool:
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
    if not await check_telegram_subscription(message.from_user.id):
        kb = InlineKeyboardMarkup(row_width=1)
        for ch in TELEGRAM_CHANNELS:
            kb.add(InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch[1:]}"))
        for link in INSTAGRAM_LINKS:
            kb.add(InlineKeyboardButton("📸 Instagram", url=link))
        kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))

        await message.answer("📢 **Obuna bo‘ling:**\nTelegram kanallar va Instagram sahifalariga obuna bo‘ling.", 
                           reply_markup=kb)
        return

    # Telegram obunasi bor bo‘lsa — Instagram menyusini chiqaramiz
    kb = InlineKeyboardMarkup(row_width=1)
    for link in INSTAGRAM_LINKS:
        kb.add(InlineKeyboardButton("📸 Instagram", url=link))
    kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_instagram"))

    await message.answer(
        "✅ Telegram kanallariga obuna bo‘lgansiz!\n\n"
        "Endi Instagram sahifalariga ham obuna bo‘ling:",
        reply_markup=kb
    )


# ================== TEKSHIRISH TUGMALARI ==================
@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_telegram(callback: types.CallbackQuery):
    if await check_telegram_subscription(callback.from_user.id):
        # Instagram menyusiga o'tkazamiz
        kb = InlineKeyboardMarkup(row_width=1)
        for link in INSTAGRAM_LINKS:
            kb.add(InlineKeyboardButton("📸 Instagram", url=link))
        kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_instagram"))

        await callback.message.edit_text(
            "✅ Telegram obunasi tasdiqlandi!\n\n"
            "Endi Instagram sahifalariga ham obuna bo‘ling:",
            reply_markup=kb
        )
    else:
        await callback.answer("❌ Telegram kanallariga hali obuna bo‘lmadingiz!", show_alert=True)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data == "check_instagram")
async def check_instagram(callback: types.CallbackQuery, state: FSMContext):
    # Instagramni avtomatik tekshirib bo'lmaydi, shuning uchun faqat tasdiqlash
    await callback.message.edit_text(
        "✅ Instagram sahifalariga obuna bo‘ldingiz deb hisoblaymiz!\n\n"
        "✍️ Endi to‘liq ismingizni kiriting:"
    )
    await Form.name.set()
    await callback.answer()


# ================== ISM QABUL QILISH VA 6 TA SERTIFIKAT ==================
@dp.message_handler(state=Form.name)
async def get_name(message: types.Message, state: FSMContext):
    name = message.text.strip()

    await message.answer(f"⏳ {name} uchun 6 ta sertifikat tayyorlanmoqda...\nBiroz kuting...")

    success_count = 0
    for key in ["template1", "template2", "template3", "template4", "template5", "template6"]:
        try:
            cert_path = generate_certificate(name, key)
            with open(cert_path, "rb") as photo:
                await bot.send_photo(
                    message.chat.id,
                    photo,
                    caption=f"✅ Sertifikat tayyor!\n👤 Ism: <b>{name}</b>\n📜 Tur: {key}"
                )
            success_count += 1
        except Exception:
            await message.answer(f"❌ {key} yaratishda xatolik yuz berdi.")

    await message.answer(f"🎉 Hammasi tugadi! Jami {success_count} ta sertifikat yuborildi.")
    await state.finish()


# ================== ADMIN BUYRUQLARI (o'zgarmadi) ==================
@dp.message_handler(commands=['addtemplate'], user_id=ADMIN_ID)
async def add_template(msg: types.Message):
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await msg.answer("❌ Sertifikat rasmini reply qilib /addtemplate yozing.")
        return
    # ... qolgan qismi sizning eski kodingizdagidek

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
        await msg.answer("❌ Format: /setpos template1 650 520 58")


if __name__ == "__main__":
    print("✅ Bot ishga tushdi!")
    executor.start_polling(dp, skip_updates=True)
