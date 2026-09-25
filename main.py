import asyncio
import random
import string
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN = "@flaybbe"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Проверка ника через t.me ---
async def check_username(session: aiohttp.ClientSession, username: str) -> bool:
    url = f"https://t.me/{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=4),
            allow_redirects=True,
        ) as resp:
            if resp.status == 404:
                return True
            text = await resp.text()
            # Если на странице есть блок профиля — ник занят
            if "tgme_page_title" in text or "tgme_page_extra" in text:
                return False
            # Заглушка без профиля — свободен
            return True
    except Exception:
        return False

# --- Генерация ника (только буквы) ---
def generate_username(length: int) -> str:
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))

# --- Клавиатуры ---
def auto_keyboard():
    b = InlineKeyboardBuilder()
    b.button(text="5 символов", callback_data="len:5")
    b.button(text="6 символов", callback_data="len:6")
    b.button(text="7 символов", callback_data="len:7")
    b.button(text="8 символов", callback_data="len:8")
    b.button(text="⬅️ Назад", callback_data="back")
    b.adjust(2, 2, 1)
    return b.as_markup()

def main_menu(user_name: str):
    text = (
        "👑 <b>TG USERNAME CHECKER</b> 👑\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Привет, <b>{user_name}</b>! 🔥\n\n"
        "Помогу найти красивый и свободный юзернейм в Telegram.\n\n"
        f"🆘 Вопросы — {ADMIN}\n\n"
        "👇 Жми кнопку снизу"
    )
    b = InlineKeyboardBuilder()
    b.button(text="🚀 Авто-поиск", callback_data="auto_menu")
    b.adjust(1)
    return text, b.as_markup()

def auto_menu():
    text = (
        "🚀 <b>АВТО-ПОИСК</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Выбери длину ников —\n"
        "найду один красивый и отдам.\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Жми длину снизу"
    )
    return text, auto_keyboard()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    u = message.from_user
    if u.first_name:
        name = u.first_name
        if u.last_name:
            name += f" {u.last_name}"
    elif u.username:
        name = f"@{u.username}"
    else:
        name = "друг"
    text, kb = main_menu(name)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "auto_menu")
async def auto_menu_handler(callback: CallbackQuery):
    text, kb = auto_menu()
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("len:"))
async def check_length(callback: CallbackQuery):
    length = int(callback.data.split(":")[1])

    await callback.message.edit_text(
        "🔍 <b>ГЕНЕРИРУЮ И ПРОВЕРЯЮ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"▸ Длина: [{length}]\n"
        "▸ Отбираю самые красивые\n\n"
        "⚡ Секунду...",
        parse_mode="HTML",
    )

    total = 0
    found = None
    checked = set()

    connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        while found is None:
            # Пачка из 60 ников
            batch = []
            while len(batch) < 60:
                u = generate_username(length)
                if u not in checked:
                    checked.add(u)
                    batch.append(u)

            results = await asyncio.gather(
                *[check_username(session, u) for u in batch],
                return_exceptions=True,
            )
            total += len(batch)

            for u, ok in zip(batch, results):
                if ok is True:
                    found = u
                    break

            if found:
                break

            try:
                await callback.message.edit_text(
                    "🔍 <b>ГЕНЕРИРУЮ И ПРОВЕРЯЮ</b>\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"▸ Длина: [{length}]\n"
                    "▸ Отбираю самые красивые\n\n"
                    f"⚡ Проверено: {total}...",
                    parse_mode="HTML",
                )
            except Exception:
                pass

    result_text = (
        "✅ <b>СВОБОДНЫЙ НИК</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "💎 <b>Твой ник:</b>\n\n"
        f"🟢 <code>@{found}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"▸ Проверено: {total}\n\n"
        "⚠️ <b>Занимай быстрее!</b>"
    )

    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=f"🔗 Открыть @{found}", url=f"https://t.me/{found}"))
    b.row(InlineKeyboardButton(text="🔄 Искать ещё", callback_data=f"len:{length}"))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="auto_menu"))

    await callback.message.edit_text(
        result_text, reply_markup=b.as_markup(), parse_mode="HTML"
    )

@dp.callback_query(F.data == "back")
async def back_handler(callback: CallbackQuery):
    u = callback.from_user
    if u.first_name:
        name = u.first_name
        if u.last_name:
            name += f" {u.last_name}"
    elif u.username:
        name = f"@{u.username}"
    else:
        name = "друг"
    text, kb = main_menu(name)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

async def main():
    logging.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
