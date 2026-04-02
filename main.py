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

# ================== TEMPLATES ==================
TEMPLATES = {
    "template1": {"file": f"{TEMPLATE_DIR}/template1.png", "x": 650, "y": 520, "size": 58, "color": (0, 0, 0)},
    "template2": {"file": f"{TEMPLATE_DIR}/template2.png", "x": 700, "y": 520, "size": 52, "color": (0, 51, 102)},
    "template3": {"file": f"{TEMPLATE_DIR}/template3.png", "x": 650, "y": 680, "size": 55, "color": (0, 80, 0)},
    "template4": {"file": f"{TEMPLATE_DIR}/template4.png", "x": 650, "y": 620, "size": 62, "color": (0, 100, 0)},
    "template5": {"file": f"{TEMPLATE_DIR}/template5.png", "x": 650, "y": 720, "size": 60, "color": (0, 70, 0)},
    "template6": {"file": f"{TEMPLATE_DIR}/template6.png", "x": 850, "y": 480, "size": 55, "color": (0, 0, 0)},
}

class Form(StatesGroup):
    name = State()

# ================== SERTIFIKAT GENERATSIYA ==================
def generate_certificate(name: str, template_key: str) -> str:
    try:
        if template_key not in TEMPLATES:
            raise Exception(f"Template {template_key} topilmadi")

        config = TEMPLATES[template_key]
       
        if not os.path.exists(config["file"]):
            raise Exception(f"Rasm topilmadi: {config['file']}")

        img = Image.open(config["file"]).convert("RGB")
        draw = ImageDraw.Draw(img)

        safe_name = "".join(c for c in name if c.isalnum() or c in " -'")[:50]
        font_path = "data/font.ttf"

        font_size = config.get("size", 60)
        color = config.get("color", (0, 0, 0))

        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            logging.warning("Font topilmadi, default ishlatilmoqda.")
            font = ImageFont.load_default()

        while font_size > 30:
            bbox = draw.textbbox((0, 0), safe_name, font=font)
            if (bbox[2] - bbox[0]) < img.size[0] - 200:
                break
            font_size -= 3
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()

        draw.text((config["x"], config["y"]), safe_name, fill=color, font=font, anchor="mm")

        output_path = f"{CERT_DIR}/{safe_name.replace(' ', '_')}_{template_key}.jpg"
        img.save(output_path, optimize=True, quality=92)
        return output_path

    except Exception as e:
        logging.error(f"{template_key} yaratishda xatolik: {e}")
        raise


# ================== FAQAT TELEGRAM OBUna TEKSHIRISH ==================
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
        
        # Telegram kanallar
        for ch in TELEGRAM_CHANNELS:
            kb.add(InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch[1:]}"))
        
        # Instagram sahifalari
        for link in INSTAGRAM_LINKS:
            kb.add(InlineKeyboardButton("📸 Instagram", url=link))
        
        # Tekshirish tugmasi
        kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))

        await message.answer(
            "📢 **Obuna bo‘ling:**\n\n"
            "Botdan foydalanish uchun quyidagilarga obuna bo‘ling:",
            reply_markup=kb
        )
        return

    # Obuna bo‘lsa darhol ism so‘raydi
    await message.answer("✍️ Iltimos, to‘liq ismingizni kiriting:")
    await Form.name.set()


# ================== TEKSHIRISH TUGMASI ==================
@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_sub_callback(callback: types.CallbackQuery, state: FSMContext):
    if await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "✅ Telegram kanallarga obuna tasdiqlandi!\n\n"
            "✍️ Endi to‘liq ismingizni kiriting:"
        )
        await Form.name.set()
    else:
        await callback.answer(
            "❌ Hali ham Telegram kanallarga obuna bo‘lmadingiz!\n"
            "Iltimos, avval kanallarga obuna bo‘ling va qayta \"Tekshirish\" tugmasini bosing.",
            show_alert=True
        )
    await callback.answer()


# ================== ISM QABUL QILISH VA 6 TA SERTIFIKAT YUBORISH ==================
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
                    caption=f"✅ Sertifikat tayyor!\n"
                            f"👤 Ism: <b>{name}</b>\n"
                            f"📜 Tur: {key}"
                )
            success_count += 1
        except Exception as e:
            await message.answer(f"❌ {key} yaratishda xatolik yuz berdi.")

    await message.answer(f"🎉 Hammasi tugadi! Jami {success_count} ta sertifikat yuborildi.")
    await state.finish()


# ================== ADMIN BUYRUQLARI ==================
@dp.message_handler(commands=['addtemplate'], user_id=ADMIN_ID)
async def add_template(msg: types.Message):
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await msg.answer("❌ Sertifikat rasmini reply qilib /addtemplate yozing.")
        return

    template_num = len(TEMPLATES) + 1
    template_key = f"template{template_num}"
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

    await msg.answer(f"✅ {template_key} qo‘shildi!\nPosition o‘zgartirish: /setpos {template_key} x y size")


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


# ================== BOT ISHGA TUSHIRISH ==================
if __name__ == "__main__":
    print("✅ Bot ishga tushdi! Rasmlar: template1.png - template6.png")
    executor.start_polling(dp, skip_updates=True)
