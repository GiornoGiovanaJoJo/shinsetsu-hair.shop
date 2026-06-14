import logging
import os
import json
import uuid
import secrets
from typing import Optional, List, Union
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import admin_finance
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import FSInputFile
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration (Hardcoded as requested) ---
TELEGRAM_BOT_TOKEN = "8508276509:AAEJd40mw7ITW3dSOeGPCAj7e7janJINiRc"
TELEGRAM_ADMIN_CHAT_IDS = [
    "8391275806", "1699147092", "482851314", "192647832",
    "7246811943", "6041951884",
]
# SOCKS5 proxy (Германия) — обход блокировки api.telegram.org на сервере
TELEGRAM_PROXY = "socks5://qJ3u0v:cLcHk7@196.19.10.162:8000"

# Админ-панель: кодовая фраза (можно переопределить через ADMIN_PASSPHRASE в .env)
ADMIN_PASSPHRASE = os.getenv("ADMIN_PASSPHRASE", "Nikitoso02")
ADMIN_SESSION_KEY = "admin_authenticated"
ADMIN_SESSION_SECRET = os.getenv("ADMIN_SESSION_SECRET", "shinsetsu-admin-session-v1")

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
            'asian': 'среднее',     # Map Asian to Average for dummy price
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
telegram_session = AiohttpSession(proxy=TELEGRAM_PROXY)
bot = Bot(token=TELEGRAM_BOT_TOKEN, session=telegram_session)
dp = Dispatcher()


async def send_telegram_text(text: str) -> None:
    for admin_id in TELEGRAM_ADMIN_CHAT_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error("Failed to send message to admin %s: %s", admin_id, e)


async def send_telegram_photos(photo_paths: List[str]) -> None:
    if not photo_paths:
        return
    media_group = [types.InputMediaPhoto(media=FSInputFile(path_)) for path_ in photo_paths]
    for admin_id in TELEGRAM_ADMIN_CHAT_IDS:
        try:
            await bot.send_media_group(chat_id=admin_id, media=media_group)
        except Exception as e:
            logger.error("Failed to send media group to admin %s: %s", admin_id, e)


def schedule_telegram(coro) -> None:
    task = asyncio.create_task(coro)
    task.add_done_callback(
        lambda t: logger.error("Telegram task failed: %s", t.exception()) if t.exception() else None
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Polling отключён: на сервере несколько воркеров вызывали TelegramConflictError.
    # Для заявок с сайта достаточно bot.send_message / send_media_group.
    try:
        admin_finance.init_finance_store()
        logger.info("Finance store initialized (seeds applied, test leads purged)")
    except Exception as e:
        logger.error("Finance store init failed: %s", e)
    yield
    try:
        await bot.session.close()
    except Exception:
        pass

app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=ADMIN_SESSION_SECRET, session_cookie="shinsetsu_admin")


def _admin_ok(request: Request) -> bool:
    return request.session.get(ADMIN_SESSION_KEY) is True


def _require_admin(request: Request) -> None:
    if not _admin_ok(request):
        raise HTTPException(status_code=401, detail="Требуется вход в админку")


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


@app.get("/admin")
async def admin_page():
    return FileResponse("admin.html")


@app.get("/admin.css")
async def admin_styles():
    return FileResponse("admin.css")


@app.get("/admin.js")
async def admin_script():
    return FileResponse("admin.js")


@app.post("/admin/login")
async def admin_login(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    phrase = str(body.get("phrase", ""))
    if not secrets.compare_digest(phrase, ADMIN_PASSPHRASE):
        raise HTTPException(status_code=401, detail="Неверная кодовая фраза")
    request.session[ADMIN_SESSION_KEY] = True
    return {"ok": True}


@app.post("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/admin/api/me")
async def admin_me(request: Request):
    _require_admin(request)
    return {"ok": True}


@app.get("/admin/api/overview")
async def admin_overview(request: Request, month: Optional[str] = None):
    _require_admin(request)
    if not month:
        from datetime import datetime, timezone
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    return {
        "summary": admin_finance.month_summary(month),
        "months": admin_finance.overview(6)["months"],
    }


@app.get("/admin/api/leads")
async def admin_leads(request: Request, month: Optional[str] = None, status: str = "all"):
    _require_admin(request)
    return {"leads": admin_finance.list_leads(month=month, status=status)}


@app.post("/admin/api/leads")
async def admin_create_lead(request: Request):
    _require_admin(request)
    payload = await request.json()
    try:
        lead = admin_finance.add_manual_lead(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"lead": lead}


@app.patch("/admin/api/leads/{lead_id}")
async def admin_update_lead(request: Request, lead_id: str):
    _require_admin(request)
    patch = await request.json()
    lead = admin_finance.update_lead(lead_id, patch)
    if not lead:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return {"lead": lead}


@app.delete("/admin/api/leads/{lead_id}")
async def admin_delete_lead(request: Request, lead_id: str):
    _require_admin(request)
    if not admin_finance.delete_lead(lead_id):
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return {"ok": True}


@app.get("/admin/api/expenses")
async def admin_expenses(request: Request, month: Optional[str] = None):
    _require_admin(request)
    return {
        "expenses": admin_finance.list_expenses(month=month),
        "total_in_store": admin_finance.count_expenses(),
    }


@app.post("/admin/api/expenses")
async def admin_add_expense(request: Request):
    _require_admin(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректные данные формы")
    try:
        expense = admin_finance.add_expense(payload)
        logger.info("Expense added id=%s amount=%s date=%s", expense.get("id"), expense.get("amount"), expense.get("date"))
        return {"expense": expense, "ok": True}
    except Exception as e:
        logger.exception("Failed to add expense: %s", e)
        raise HTTPException(status_code=500, detail=f"Не удалось сохранить расход: {e}")


@app.patch("/admin/api/expenses/{expense_id}")
async def admin_patch_expense(request: Request, expense_id: str):
    _require_admin(request)
    patch = await request.json()
    expense = admin_finance.update_expense(expense_id, patch)
    if not expense:
        raise HTTPException(status_code=404, detail="Расход не найден")
    return {"expense": expense}


@app.delete("/admin/api/expenses/{expense_id}")
async def admin_delete_expense(request: Request, expense_id: str):
    _require_admin(request)
    if not admin_finance.delete_expense(expense_id):
        raise HTTPException(status_code=404, detail="Расход не найден")
    return {"ok": True}


@app.get("/robots.txt", response_class=Response)
async def read_robots():
    content = """User-agent: * 
Allow: /
Disallow: /cart/
Disallow: /admin
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
    "app.log", ".env", "nginx.conf.template", "admin_finance.py",
    "admin.html", "admin.css", "admin.js",
]

@app.get("/{filename}")
async def block_sensitive_files(filename: str):
    if filename in SENSITIVE_FILES or filename.endswith(('.py', '.sh', '.bak')):
        raise HTTPException(status_code=404)
    raise HTTPException(status_code=404)

@app.post("/api/calculate")
async def handle_calculate(
    color: str = Form(...),
    length: str = Form(...),
    structure: str = Form(...),
    condition: str = Form(...),
    name: str = Form(...),
    phone: str = Form(...),
    city: str = Form(...),
    email: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    photos: Union[List[UploadFile], UploadFile, None] = File(None),
):
    try:
        uploaded_photos: List[UploadFile] = []
        if photos is not None:
            uploaded_photos = photos if isinstance(photos, list) else [photos]
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

        condition_map = {
            'slavic': 'славянские',
            'european': 'европейские',
            'asian': 'азиатские'
        }
        display_condition = condition_map.get(condition.lower(), condition).capitalize()

        # Calculate Price
        price = calculate_price(length, color, structure)
        
        # Save photos
        photo_paths = []
        if uploaded_photos:
            for photo in uploaded_photos:
                if photo.filename:
                    ext = os.path.splitext(photo.filename)[1] or ".jpg"
                    safe_name = f"{uuid.uuid4().hex}{ext}"
                    file_path = os.path.join(UPLOAD_DIR, safe_name)
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
            f"🧬 Тип: {display_condition}\n"
            f"💵 <b>Оценка: ~{price} ₽</b>\n\n"
            f"<b>Контакты:</b>\n"
            f"👤 ФИО: {name}\n"
            f"📱 Номер: {phone}\n"
            f"🏙 Город: {city}\n"
            f"📧 Почта: {email if email else 'Нет'}\n"
            f"💬 Сообщение: {message if message else 'Нет'}\n\n"
            f"📸 Прикреплено фото: {photo_count} шт."
        )
        
        schedule_telegram(send_telegram_text(msg_text))
        if photo_paths:
            schedule_telegram(send_telegram_photos(photo_paths))

        if not admin_finance.is_test_submission(name, phone, city):
            admin_finance.add_calculate_lead(
                name=name,
                phone=phone,
                city=city,
                email=email,
                message=message,
                length=length,
                color=color,
                structure=structure,
                condition=condition,
                estimated_price=price,
                photo_count=photo_count,
            )

        return JSONResponse(content={"success": True, "price": price, "message": "Расчет отправлен"})

    except Exception as e:
        logger.exception("Error in calculate: %s", e)
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
        schedule_telegram(send_telegram_text(msg))
        if not admin_finance.is_test_submission(fullname, phone, ""):
            admin_finance.add_callback_lead(fullname=fullname, phone=phone)
        return JSONResponse(content={"success": True, "message": "Заявка принята"})
    except Exception as e:
        logger.exception("Error in callback: %s", e)
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