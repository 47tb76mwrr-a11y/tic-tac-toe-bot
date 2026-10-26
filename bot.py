import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.chat_action import ChatActionSender

BOT_TOKEN = "8911367022:AAH7lRA49r19-a_EUr_97P2xjBgcNAlb4tc"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
games = {}
scores = {}

EMPTY = "⬜"
X = "❌"
O = "⭕"

WIN_CONDITIONS = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]

def symbol_to_text(s):
    if s == "X":
        return X
    if s == "O":
        return O
    return EMPTY

def get_board_keyboard(board, game_id):
    builder = InlineKeyboardBuilder()
    for i in range(9):
        text = symbol_to_text(board[i])
        builder.button(text=text, callback_data=f"move:{game_id}:{i}")
    builder.adjust(3)
    return builder.as_markup()

def get_side_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Играть за {X}", callback_data="side:X")
    builder.button(text=f"Играть за {O}", callback_data="side:O")
    builder.adjust(2)
    return builder.as_markup()

def check_winner(board, symbol):
    for a, b, c in WIN_CONDITIONS:
        if board[a] == board[b] == board[c] == symbol:
            return True
    return False

def find_winning_move(board, symbol):
    for a, b, c in WIN_CONDITIONS:
        line = [board[a], board[b], board[c]]
        if line.count(symbol) == 2 and line.count(" ") == 1:
            return [a, b, c][line.index(" ")]
    return None

def bot_move(board, bot_symbol, player_symbol):
    move = find_winning_move(board, bot_symbol)
    if move is not None:
        return move
    move = find_winning_move(board, player_symbol)
    if move is not None:
        return move
    if board[4] == " ":
        return 4
    for i in [0, 2, 6, 8]:
        if board[i] == " ":
            return i
    for i in range(9):
        if board[i] == " ":
            return i
    return None

def get_score(user_id):
    return scores.setdefault(user_id, {"wins": 0, "losses": 0, "draws": 0})

def format_score(score):
    return f"📊 Счёт: ты {score['wins']} : {score['losses']} бот (ничьих: {score['draws']})"

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🎮 <b>Крестики-нолики</b>\n\nВыбери, за кого играешь:",
        parse_mode="HTML",
        reply_markup=get_side_keyboard()
    )

@dp.callback_query(F.data.startswith("side:"))
async def choose_side(callback: types.CallbackQuery):
    side = callback.data.split(":")[1]
    user_id = callback.from_user.id
    board = [" "] * 9
    games[user_id] = {"board": board, "player": side, "bot": "O" if side == "X" else "X"}
    game = games[user_id]
    player_sym = symbol_to_text(game["player"])
    await callback.message.edit_text(
        f"🎮 <b>Крестики-нолики</b>\n\nТы играешь за {player_sym}. Твой ход:",
        parse_mode="HTML",
        reply_markup=get_board_keyboard(board, user_id)
    )
    if game["player"] == "O":
        async with ChatActionSender.typing(bot=bot, chat_id=user_id):
            await asyncio.sleep(1.5)
            move = bot_move(board, "X", "O")
            board[move] = "X"
        await callback.message.edit_text(
            f"🎮 <b>Крестики-нолики</b>\n\nТы играешь за {O}. Бот сходил {X}. Твой ход:",
            parse_mode="HTML",
            reply_markup=get_board_keyboard(board, user_id)
        )
    await callback.answer()

@dp.callback_query(F.data.startswith("move:"))
async def handle_move(callback: types.CallbackQuery):
    _, game_id, index = callback.data.split(":")
    game_id = int(game_id)
    index = int(index)
    if game_id not in games:
        await callback.answer("Игра не найдена. Напиши /start")
        return
    game = games[game_id]
    board = game["board"]
    player = game["player"]
    bot_sym = game["bot"]
    if board[index] != " ":
        await callback.answer("Эта клетка уже занята!")
        return

    board[index] = player
    score = get_score(game_id)

    await callback.message.edit_reply_markup(
        reply_markup=get_board_keyboard(board, game_id)
    )

    if check_winner(board, player):
        score["wins"] += 1
        await callback.message.edit_text(
            f"🎉 Ты победил!\n\n{format_score(score)}\n\nНапиши /start чтобы сыграть ещё."
        )
        del games[game_id]
        await callback.answer()
        return
    if " " not in board:
        score["draws"] += 1
        await callback.message.edit_text(
            f"🤝 Ничья!\n\n{format_score(score)}\n\nНапиши /start чтобы сыграть ещё."
        )
        del games[game_id]
        await callback.answer()
        return

    async with ChatActionSender.typing(bot=bot, chat_id=game_id):
        await asyncio.sleep(1.5)
        move = bot_move(board, bot_sym, player)
        board[move] = bot_sym

    if check_winner(board, bot_sym):
        score["losses"] += 1
        await callback.message.edit_text(
            f"😢 Победил бот ({symbol_to_text(bot_sym)}).\n\n{format_score(score)}\n\nНапиши /start чтобы сыграть ещё."
        )
        del games[game_id]
        await callback.answer()
        return
    if " " not in board:
        score["draws"] += 1
        await callback.message.edit_text(
            f"🤝 Ничья!\n\n{format_score(score)}\n\nНапиши /start чтобы сыграть ещё."
        )
        del games[game_id]
        await callback.answer()
        return

    await callback.message.edit_reply_markup(
        reply_markup=get_board_keyboard(board, game_id)
    )
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
