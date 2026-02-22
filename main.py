import logging
import os
import json
from typing import Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration (Hardcoded as requested) ---
TELEGRAM_BOT_TOKEN = "8508276509:AAEJd40mw7ITW3dSOeGPCAj7e7janJINiRc"
TELEGRAM_ADMIN_CHAT_IDS = ["8391275806", "1699147092"]

# --- Calculator Logic (Ported) ---
PRICE_TABLE = {
    '40-50': {
        'блонд': {'славянка': 25000, 'среднее': 20000, 'густые': 25000},
        'светло-русые': {'славянка': 25000, 'среднее': 20000, 'густые': 25000},
        'русые': {'славянка': 20000, 'среднее': 18000, 'густые': 20000},
        'темно-русые': {'славянка': 20000, 'среднее': 18000, 'густые': 20000},
        'каштановые': {'славянка': 20000, 'среднее': 18000, 'густые': 20000},
    },
    '50-60': {
        'блонд': {'славянка': 35000, 'среднее': 30000, 'густые': 35000},
        'светло-русые': {'славянка': 35000, 'среднее': 30000, 'густые': 35000},
        'русые': {'славянка': 30000, 'среднее': 28000, 'густые': 30000},
        'темно-русые': {'славянка': 30000, 'среднее': 28000, 'густые': 30000},
        'каштановые': {'славянка': 28000, 'среднее': 25000, 'густые': 28000},
    },
    '60-80': {
        'блонд': {'славянка': 45000, 'среднее': 40000, 'густые': 45000},
        'светло-русые': {'славянка': 45000, 'среднее': 40000, 'густые': 45000},
        'русые': {'славянка': 40000, 'среднее': 38000, 'густые': 40000},
        'темно-русые': {'славянка': 40000, 'среднее': 38000, 'густые': 40000},
        'каштановые': {'славянка': 35000, 'среднее': 35000, 'густые': 38000},
    },
    '80-100': {
        'блонд': {'славянка': 55000, 'среднее': 50000, 'густые': 55000},
        'светло-русые': {'славянка': 55000, 'среднее': 50000, 'густые': 55000},
        'русые': {'славянка': 50000, 'среднее': 48000, 'густые': 50000},
        'темно-русые': {'славянка': 48000, 'среднее': 45000, 'густые': 48000},
        'каштановые': {'славянка': 48000, 'среднее': 45000, 'густые': 48000},
    },
    '100+': {
        'блонд': {'славянка': 65000, 'среднее': 60000, 'густые': 65000},
        'светло-русые': {'славянка': 65000, 'среднее': 60000, 'густые': 65000},
        'русые': {'славянка': 60000, 'среднее': 58000, 'густые': 60000},
        'темно-русые': {'славянка': 58000, 'среднее': 55000, 'густые': 58000},
        'каштановые': {'славянка': 55000, 'среднее': 55000, 'густые': 58000},
    }
}

def calculate_price(length_str: str, color: str, structure: str) -> int:
    try:
        # 1. Determine length range
        length_range = None
        length_num = 50 

        clean_length = str(length_str).strip().lower()
        if clean_length == '100+':
            length_range = '100+'
        elif '-' in clean_length:
            try:
                length_num = int(clean_length.split('-')[0])
            except:
                pass
        else:
            try:
                length_num = int(clean_length)
            except:
                pass
        
        if length_range is None:
            if length_num < 40: length_num = 40
            if length_num > 150: length_num = 150
            
            if length_num < 50: length_range = '40-50'
            elif length_num < 60: length_range = '50-60'
            elif length_num < 80: length_range = '60-80'
            elif length_num < 100: length_range = '80-100'
            else: length_range = '100+'

        # 2. Normalize color
        color_map = {
            'blonde': 'блонд', 
            'light-brown': 'русые', # HTML Label: "Русые" -> Backend 'русые'
            'brown': 'каштановые',  # HTML Label: "Каштановые"
            'black': 'каштановые',  # Map Black to Chestnut (Dark)
            'grey': 'русые',        # Map Grey to Light Brown/Neutral
            'red': 'каштановые',    # Map Red to Chestnut
            # Legacy/Cyrillic fallbacks
            'блонд': 'блонд',
            'светло-русые': 'светло-русые',
            'русые': 'русые',
            'темно-русые': 'темно-русые',
            'каштановые': 'каштановые'
        }
        color_key = color_map.get(color.lower(), 'блонд')

        # 3. Normalize structure
        struct_map = {
            'straight': 'славянка', # HTML Label: "Прямые"
            'wavy': 'среднее',      # HTML Label: "Волнистые"
            'curly': 'густые',      # HTML Label: "Кудрявые" -> Backend 'густые'
            # Legacy/Cyrillic fallbacks
            'славянка': 'славянка',
            'среднее': 'среднее',
            'густые': 'густые',
            'тонкие': 'славянка'
        }
        struct_key = struct_map.get(structure.lower(), 'среднее')

        # 4. Lookup
        price = PRICE_TABLE.get(length_range, {}).get(color_key, {}).get(struct_key, 30000)
        return int(price)

    except Exception as e:
        logger.error(f"Calculation error: {e}")
        return 30000

# --- App Setup ---
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    polling_task = asyncio.create_task(dp.start_polling(bot))
    yield
    # Shutdown
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    try:
        await bot.session.close()
    except Exception:
        pass

app = FastAPI(lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="."), name="static")
app.mount("/templates", StaticFiles(directory="templates"), name="templates_static")
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts_static")

# Jinja2 setup
templates = Jinja2Templates(directory=".")

def get_content():
    try:
        with open("content.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
async def read_index(request: Request):
    content = get_content()
    return templates.TemplateResponse("index.html", {"request": request, "content": content})

@app.get("/styles.css")
async def read_styles():
    return FileResponse("styles.css")

@app.get("/script.js")
async def read_script():
    return FileResponse("script.js")
    
@app.get("/robots.txt", response_class=Response)
async def read_robots():
    content = """User-agent: * 
Allow: /
Disallow: /cart/
Sitemap: https://shinsetsu-hair.shop/sitemap.xml"""
    return Response(content=content, media_type="text/plain")

@app.get("/sitemap.xml", response_class=Response)
async def generate_sitemap():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://shinsetsu-hair.shop/</loc><priority>1.0</priority></url>
</urlset>"""
    return Response(content=content, media_type="application/xml")

@app.exception_handler(404)
async def custom_404_handler(request, exc):
    return JSONResponse(status_code=404, content={"message": "Страница не найдена. Пожалуйста, вернитесь на главную: https://shinsetsu-hair.shop/"})

@app.get("/yandex_6407bd5a232ac6e8.html", response_class=Response)
async def read_yandex_verification():
    return FileResponse("yandex_6407bd5a232ac6e8.html")

# Block access to sensitive server-side files
SENSITIVE_FILES = [
    "main.py", "deploy.sh", "content.json", "requirements.txt",
    "app.log", ".env", "nginx.conf.template",
]

@app.get("/{filename}")
async def block_sensitive_files(filename: str):
    if filename in SENSITIVE_FILES or filename.endswith(('.py', '.sh', '.bak')):
        raise HTTPException(status_code=404)
    raise HTTPException(status_code=404)

@app.post("/api/calculate")
async def handle_calculate(
    length: str = Form(...),
    color: str = Form(...),
    structure: str = Form(...),
    name: str = Form(...),
    phone: str = Form(...),
    city: str = Form(...),
    email: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    photos: List[UploadFile] = File(None)
):
    try:
        # 1. Logic (Normalization) - kept same
        # ... (Duplicate logic for mapping to ensure we have keys) ...
        # Ideally, we should refactor calculate_price to return normalized keys too, 
        # but to keep it safe, I'll re-map here for display or rely on the function.
        # Actually, let's just re-use the maps locally for display, or make calculate_price return them.
        # For minimal disruption, I will re-normalize here for the message display.
        
        # Normalize for display
        color_map = {
            'blonde': 'блонд', 'light-brown': 'русые', 'brown': 'каштановые', 
            'black': 'каштановые', 'grey': 'русые', 'red': 'каштановые',
            'блонд': 'блонд', 'светло-русые': 'светло-русые', 'русые': 'русые',
            'темно-русые': 'темно-русые', 'каштановые': 'каштановые'
        }
        display_color = color_map.get(color.lower(), color).capitalize()

        struct_map = {
            'straight': 'славянка', 'wavy': 'среднее', 'curly': 'густые',
            'славянка': 'славянка', 'среднее': 'среднее', 'густые': 'густые', 'тонкие': 'славянка'
        }
        display_structure = struct_map.get(structure.lower(), structure).capitalize()

        # Calculate Price
        price = calculate_price(length, color, structure)
        
        # Save photos
        photo_paths = []
        if photos:
            for photo in photos:
                if photo.filename:
                    file_path = os.path.join(UPLOAD_DIR, photo.filename)
                    with open(file_path, "wb") as f:
                        f.write(await photo.read())
                    photo_paths.append(file_path)

        # Notify Admin via Telegram
        photo_count = len(photo_paths)
        msg_text = (
            f"💰 <b>Новая заявка на расчет!</b>\n\n"
            f"<b>Параметры волос:</b>\n"
            f"📏 Длина: {length}\n"
            f"🎨 Цвет: {display_color}\n"
            f"💇 Структура: {display_structure}\n"
            f"💵 <b>Оценка: ~{price} ₽</b>\n\n"
            f"<b>Контакты:</b>\n"
            f"👤 ФИО: {name}\n"
            f"📱 Номер: {phone}\n"
            f"🏙 Город: {city}\n"
            f"📧 Почта: {email if email else 'Нет'}\n"
            f"💬 Сообщение: {message if message else 'Нет'}\n\n"
            f"📸 Прикреплено фото: {photo_count} шт."
        )
        
        # Send text
        for admin_id in TELEGRAM_ADMIN_CHAT_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=msg_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Failed to send message to admin {admin_id}: {e}")
        
        # Send photos
        if photo_paths:
            media_group = []
            for path_ in photo_paths:
                from aiogram.types import FSInputFile
                media_group.append(types.InputMediaPhoto(media=FSInputFile(path_)))
            
            if media_group:
                for admin_id in TELEGRAM_ADMIN_CHAT_IDS:
                    try:
                        await bot.send_media_group(chat_id=admin_id, media=media_group)
                    except Exception as e:
                        logger.error(f"Failed to send media group to admin {admin_id}: {e}")

        return JSONResponse(content={"success": True, "price": price, "message": "Расчет отправлен"})

    except Exception as e:
        logger.error(f"Error in calculate: {e}")
        return JSONResponse(content={"success": False, "message": "Ошибка сервера"}, status_code=500)

@app.post("/api/callback")
async def handle_callback(
    fullname: str = Form(...),
    phone: str = Form(...)
):
    try:
        msg = (
            f"📞 <b>Заказ обратного звонка!</b>\n\n"
            f"👤 Имя/ФИО: {fullname}\n"
            f"☎️ Телефон: {phone}"
        )
        for admin_id in TELEGRAM_ADMIN_CHAT_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=msg, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Failed to send callback to admin {admin_id}: {e}")
        return JSONResponse(content={"success": True, "message": "Заявка принята"})
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        return JSONResponse(content={"success": False, "message": "Ошибка сервера"}, status_code=500)

# --- Bot Handlers (Simple User-Facing) ---
@dp.message()
async def echo_handler(message: types.Message):
    """
    Simple echo or welcome handler. 
    The user can expand this later based on the original bot logic if required.
    For now, it just acknowledges receipt.
    """
    if message.text == '/start':
        await message.answer("Привет! Я бот Shinsetsu Hair. Оставьте заявку на сайте, и мы свяжемся с вами!")
    else:
        # Forward user messages to admin just in case
        for admin_id in TELEGRAM_ADMIN_CHAT_IDS:
            try:
                await bot.forward_message(chat_id=admin_id, from_chat_id=message.chat.id, message_id=message.message_id)
            except Exception as e:
                logger.error(f"Failed to forward message to admin {admin_id}: {e}")
        await message.answer("Ваше сообщение передано администратору.")



# Mount root last to serve any other static files
app.mount("/", StaticFiles(directory=".", html=True), name="site")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)