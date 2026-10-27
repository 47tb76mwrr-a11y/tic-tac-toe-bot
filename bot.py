# -*- coding: utf-8 -*-
# Игровой центр + Тайный Санта

import asyncio
import logging
import random
import string
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.chat_action import ChatActionSender

BOT_TOKEN = "8911367022:AAH7lRA49r19-a_EUr_97P2xjBgcNAlb4tc"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

EMPTY = "⬜"
X = "❌"
O = "⭕"
WIN_CONDITIONS = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]

bot_games = {}
bot_scores = {}
wordle_games = {}     
waiting_for_code = {}
santa_games = {} 
waiting_for_santa_code = {} 
waiting_for_santa_name = {} # user_id -> room_code (для входа)
waiting_for_creator_name = {} # user_id -> count (для создателя)

def init_db():
    conn = sqlite3.connect("game.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            room_code TEXT PRIMARY KEY, player_x INTEGER, player_o INTEGER,
            board TEXT, turn TEXT, status TEXT, msg_x INTEGER, msg_o INTEGER,
            score_x INTEGER DEFAULT 0, score_o INTEGER DEFAULT 0
        )
    ''')
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN score_x INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE games ADD COLUMN score_o INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE games ADD COLUMN msg_x INTEGER")
        cursor.execute("ALTER TABLE games ADD COLUMN msg_o INTEGER")
    except sqlite3.OperationalError: pass 
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect("game.db")

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def symbol_to_text(s):
    if s == "X": return X
    if s == "O": return O
    return EMPTY

def check_winner(board, symbol):
    for a, b, c in WIN_CONDITIONS:
        if board[a] == board[b] == board[c] == symbol: return True
    return False

# --- Клавиатуры ---
def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Крестики-нолики", callback_data="menu:tictactoe")
    builder.button(text="🔢 Цифровой Wordle", callback_data="wordle:bot")
    builder.button(text="🎅 Тайный Санта", callback_data="menu:santa")
    builder.adjust(1)
    return builder.as_markup()

def get_game_mode_keyboard(game_prefix):
    builder = InlineKeyboardBuilder()
    builder.button(text="🤖 С ботом", callback_data=f"{game_prefix}:bot")
    builder.button(text="🌐 По сети", callback_data=f"{game_prefix}:net")
    builder.button(text="🔙 Назад", callback_data="mode:main")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_side_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Играть за {X}", callback_data="side:X")
    builder.button(text=f"Играть за {O}", callback_data="side:O")
    builder.button(text="🔙 Назад", callback_data="menu:tictactoe")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_bot_board_keyboard(board, game_id):
    builder = InlineKeyboardBuilder()
    for i in range(9):
        builder.button(text=symbol_to_text(board[i]), callback_data=f"botmove:{game_id}:{i}")
    builder.adjust(3)
    return builder.as_markup()

def get_net_board_keyboard(board, room_code):
    builder = InlineKeyboardBuilder()
    for i in range(9):
        builder.button(text=symbol_to_text(board[i]), callback_data=f"netmove:{room_code}:{i}")
    builder.adjust(3)
    return builder.as_markup()

def get_rematch_keyboard(room_code):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Играть снова", callback_data=f"rematch:{room_code}")
    builder.adjust(1)
    return builder.as_markup()

def get_game_over_keyboard(game_prefix):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Играть снова", callback_data=f"{game_prefix}:bot")
    builder.button(text="🏠 В меню", callback_data="mode:main")
    builder.adjust(1)
    return builder.as_markup()

def get_santa_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎄 Создать комнату", callback_data="santa:create")
    builder.button(text="🔑 Войти в комнату", callback_data="santa:join")
    builder.button(text="🔙 Назад", callback_data="mode:main")
    builder.adjust(1)
    return builder.as_markup()

def get_santa_count_keyboard():
    builder = InlineKeyboardBuilder()
    for i in range(2, 11):
        builder.button(text=str(i), callback_data=f"santa_count:{i}")
    builder.button(text="🔙 Отмена", callback_data="menu:santa")
    builder.adjust(5, 5, 1)
    return builder.as_markup()

# --- Главное меню ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🎮 <b>Игровой центр</b>\n\nВыбери игру:", parse_mode="HTML", reply_markup=get_main_menu_keyboard())

@dp.callback_query(F.data == "mode:main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("🎮 <b>Игровой центр</b>\n\nВыбери игру:", parse_mode="HTML", reply_markup=get_main_menu_keyboard())
    await callback.answer()

# --- Меню игр ---
@dp.callback_query(F.data == "menu:tictactoe")
async def menu_tictactoe(callback: types.CallbackQuery):
    text = (
        "❌ <b>Крестики-нолики</b>\n\n"
        "📜 <b>Правила:</b>\n"
        "Игроки по очереди ставят на свободные клетки поля 3×3 свои знаки (один всегда ❌, другой ⭕). "
        "Первый, выстроивший в ряд 3 своих знака по вертикали, горизонтали или диагонали, выигрывает.\n\n"
        "Выбери режим:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_game_mode_keyboard("tictactoe"))
    await callback.answer()

# ==========================================
# ЦИФРОВОЙ WORDLE
# ==========================================
def generate_wordle_secret():
    return "".join([str(random.randint(0, 9)) for _ in range(4)])

def check_wordle(secret, guess):
    result = ["⬛"] * 4
    secret_list = list(secret)
    guess_list = list(guess)
    for i in range(4):
        if guess_list[i] == secret_list[i]:
            result[i] = "🟩"
            secret_list[i] = None
            guess_list[i] = None
    for i in range(4):
        if guess_list[i] is not None and guess_list[i] in secret_list:
            result[i] = "🟨"
            secret_list[secret_list.index(guess_list[i])] = None
    return "".join(result)

@dp.callback_query(F.data == "wordle:bot")
async def wordle_bot_start(callback: types.CallbackQuery):
    text = (
        "🔢 <b>Цифровой Wordle</b>\n\n"
        "📜 <b>Правила:</b>\n"
        "Бот загадывает 4-значный код (цифры могут повторяться). "
        "Ты вводишь свои 4 цифры, а бот подсвечивает их цветами:\n\n"
        "🟩 — цифра на своём месте\n"
        "🟨 — цифра есть, но не на своём месте\n"
        "⬛ — такой цифры нет\n\n"
        "У тебя 6 попыток, чтобы угадать код.\n\n"
        "Напиши свою первую догадку (например: <code>1234</code>):"
    )
    msg = await callback.message.edit_text(text, parse_mode="HTML")
    user_id = callback.from_user.id
    secret = generate_wordle_secret()
    wordle_games[user_id] = {"secret": secret, "attempts": 0, "history": [], "msg_id": msg.message_id}
    await callback.answer()

# ==========================================
# ТАЙНЫЙ САНТА
# ==========================================
@dp.callback_query(F.data == "menu:santa")
async def menu_santa(callback: types.CallbackQuery):
    text = (
        "🎅 <b>Тайный Санта</b> 🎄\n\n"
        "📜 <b>Как это работает:</b>\n"
        "1. Создатель комнаты выбирает количество участников (2-10).\n"
        "2. Бот выдаёт код комнаты. Создатель скидывает код друзьям.\n"
        "3. Друзья заходят в бота, нажимают «Войти в комнату», вводят код и пишут своё имя.\n"
        "4. Когда все зашли, бот тайно распределяет, кто кому дарит подарок, и присылает каждому имя в личку.\n\n"
        "Выбери действие:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_santa_menu_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "santa:create")
async def santa_create(callback: types.CallbackQuery):
    text = "🎄 <b>Создание комнаты</b>\n\nВыбери общее количество участников (включая тебя):"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_santa_count_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("santa_count:"))
async def santa_count_selected(callback: types.CallbackQuery):
    count = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    # Запоминаем, что создатель выбрал количество и теперь должен ввести имя
    waiting_for_creator_name[user_id] = count
    
    await callback.message.edit_text(
        "🎅 Отлично! Теперь напиши своё имя (как тебя будут называть в игре):"
    )
    await callback.answer()

@dp.callback_query(F.data == "santa:join")
async def santa_join_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    waiting_for_santa_code[user_id] = True
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Отмена", callback_data="menu:santa")
    await callback.message.edit_text(
        "🔑 <b>Вход в комнату</b>\n\n"
        "Напиши 4-значный код комнаты, который тебе дал создатель:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# ==========================================
# ОБРАБОТЧИК ТЕКСТА
# ==========================================
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_all_text_input(message: types.Message):
    user_id = message.from_user.id
    
    # --- Ожидание имени СОЗДАТЕЛЯ ---
    if user_id in waiting_for_creator_name:
        count = waiting_for_creator_name.pop(user_id)
        name = message.text.strip()
        room_code = generate_code()
        
        # Создаем комнату, сразу добавляя создателя в список игроков
        santa_games[room_code] = {
            "creator_id": user_id,
            "max_players": count,
            "players": {user_id: name},
            "status": "waiting",
            "creator_msg_id": message.message_id + 1 # Примерно
        }
        
        # Отправляем новое сообщение с кодом комнаты
        msg = await message.answer(
            f"✅ Комната создана!\n\n"
            f"Код комнаты: <code>{room_code}</code>\n"
            f"Количество участников: {count}\n\n"
            f"Скинь этот код друзьям. Они должны нажать «Войти в комнату» и ввести его.\n\n"
            f"👥 Участники (1/{count}):\n• {name}",
            parse_mode="HTML"
        )
        # Обновляем ID сообщения
        santa_games[room_code]["creator_msg_id"] = msg.message_id
        
        # Если вдруг count = 1 (хотя мы ограничили от 2), то сразу старт
        if count == 1:
             await start_santa_game(room_code, santa_games[room_code])
        return

    # --- Ожидание кода Тайного Санты ---
    if waiting_for_santa_code.get(user_id):
        waiting_for_santa_code.pop(user_id, None)
        room_code = message.text.strip().upper()
        
        if room_code not in santa_games:
            await message.answer("❌ Комната не найдена. Проверь код.")
            return
            
        game = santa_games[room_code]
        if game["status"] != "waiting":
            await message.answer("❌ Игра уже началась, входить поздно.")
            return
            
        if user_id in game["players"]:
            await message.answer("❌ Ты уже в этой комнате.")
            return

        waiting_for_santa_name[user_id] = room_code
        await message.answer("🎅 Как тебя зовут? Напиши своё имя:")
        return

    # --- Ожидание имени УЧАСТНИКА ---
    if user_id in waiting_for_santa_name:
        room_code = waiting_for_santa_name[user_id]
        name = message.text.strip()
        
        if room_code not in santa_games:
            await message.answer("❌ Комната не найдена.")
            del waiting_for_santa_name[user_id]
            return
            
        game = santa_games[room_code]
        
        if name in game["players"].values():
            await message.answer(f"❌ Имя «{name}» уже занято. Введи другое.")
            return
            
        # Добавляем игрока
        game["players"][user_id] = name
        del waiting_for_santa_name[user_id]
        
        # Обновляем сообщение у создателя
        creator_id = game["creator_id"]
        creator_msg_id = game["creator_msg_id"]
        count = game["max_players"]
        
        players_list = "\n".join([f"• {n}" for n in game["players"].values()])
        text = (
            f"✅ Комната создана!\n\n"
            f"Код комнаты: <code>{room_code}</code>\n"
            f"Количество участников: {count}\n\n"
            f"Скинь этот код друзьям. Они должны нажать «Войти в комнату» и ввести его.\n\n"
            f"👥 Участники ({len(game['players'])}/{count}):\n{players_list}"
        )
        
        try:
            await bot.edit_message_text(
                chat_id=creator_id,
                message_id=creator_msg_id,
                text=text,
                parse_mode="HTML"
            )
        except Exception:
            pass 
        
        await message.answer(f"✅ Ты в игре, {name}!\n\nЖдём остальных...")
        
        # Проверяем, все ли зашли
        if len(game["players"]) == game["max_players"]:
            game["status"] = "started"
            await start_santa_game(room_code, game)
        return

    # --- Ввод для Цифрового Wordle ---
    if user_id in wordle_games:
        guess = message.text.strip()
        if len(guess) != 4 or not guess.isdigit():
            await message.answer("❌ Нужно ввести ровно 4 цифры. Попробуй ещё раз.")
            return

        try: await message.delete()
        except Exception: pass

        game = wordle_games[user_id]
        game["attempts"] += 1
        secret = game["secret"]
        
        result = check_wordle(secret, guess)
        game["history"].append(f"<code>{guess}</code>  {result}")
        
        history_text = "\n".join(game["history"])
        
        if guess == secret:
            await message.answer(
                f"🎉 Поздравляю! Ты угадал код <b>{secret}</b> за {game['attempts']} попыток!\n\n{history_text}",
                parse_mode="HTML",
                reply_markup=get_game_over_keyboard("wordle")
            )
            del wordle_games[user_id]
        elif game["attempts"] >= 6:
            await message.answer(
                f"😢 Попытки закончились! Я загадал <b>{secret}</b>.\n\n{history_text}",
                parse_mode="HTML",
                reply_markup=get_game_over_keyboard("wordle")
            )
            del wordle_games[user_id]
        else:
            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=game["msg_id"],
                    text=f"🔢 <b>Цифровой Wordle</b>\n\nТвои попытки:\n{history_text}\n\nПопытка {game['attempts'] + 1}/6. Введи следующую догадку:",
                    parse_mode="HTML"
                )
            except Exception:
                msg = await message.answer(f"🔢 <b>Цифровой Wordle</b>\n\nТвои попытки:\n{history_text}\n\nПопытка {game['attempts'] + 1}/6. Введи следующую догадку:", parse_mode="HTML")
                game["msg_id"] = msg.message_id
        return

    # --- Ввод кода комнаты для крестиков ---
    if waiting_for_code.get(user_id):
        waiting_for_code.pop(user_id, None)
        room_code = message.text.strip().upper()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games WHERE room_code = ?", (room_code,))
        row = cursor.fetchone()
        conn.close()
        if row:
            (_, player_x, player_o, board_str, turn, status, msg_x, msg_o, _, _) = row
            if status != "waiting": await message.answer("❌ Эта комната уже занята или игра уже идёт.")
            elif player_x == user_id: await message.answer("❌ Ты не можешь играть сам с собой.")
            else:
                board = list(board_str)
                try:
                    sent_msg_x = await bot.send_message(player_x, f"🎮 Сетевая игра началась!\n\nТы играешь за {X}. Твой ход:", reply_markup=get_net_board_keyboard(board, room_code))
                    msg_x_id = sent_msg_x.message_id
                except Exception: msg_x_id = None
                sent_msg_o = await message.answer(f"🎮 Сетевая игра началась!\n\nТы играешь за {O}.\nТвой ход будет после {X}.", reply_markup=get_net_board_keyboard(board, room_code))
                msg_o_id = sent_msg_o.message_id
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE games SET player_o = ?, status = ?, msg_x = ?, msg_o = ? WHERE room_code = ?", (user_id, "playing", msg_x_id, msg_o_id, room_code))
                conn.commit()
                conn.close()
            return

# Вспомогательная функция для запуска Санты
async def start_santa_game(room_code, game):
    user_ids = list(game["players"].keys())
    names = list(game["players"].values())
    shuffled_names = names[1:] + [names[0]]
    
    for i, uid in enumerate(user_ids):
        target_name = shuffled_names[i]
        try:
            await bot.send_message(
                uid,
                f"🎅 <b>Тайный Санта начался!</b> 🎄\n\n"
                f"Ты даришь подарок: <b>{target_name}</b>!\n\n"
                f"🤫 Только тссс, никому не говори!",
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    try:
        await bot.edit_message_text(
            chat_id=game["creator_id"],
            message_id=game["creator_msg_id"],
            text="🎉 <b>Все собрались!</b> Имена распределены. Каждый участник получил имя в личку.",
            parse_mode="HTML"
        )
    except Exception:
        pass

# ==========================================
# ЛОГИКА СЕТЕВЫХ КРЕСТИКОВ-НОЛИКОВ
# ==========================================
@dp.callback_query(F.data == "tictactoe:bot")
async def tictactoe_bot_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ <b>Крестики-нолики с ботом</b>\n\nВыбери, за кого играешь:", parse_mode="HTML", reply_markup=get_side_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "tictactoe:net")
async def tictactoe_net_menu(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать комнату", callback_data="net:create")
    builder.button(text="🔑 Войти в комнату", callback_data="net:join")
    builder.button(text="🔙 Назад", callback_data="menu:tictactoe")
    builder.adjust(1)
    await callback.message.edit_text("🌐 <b>Крестики-нолики по сети</b>\n\nВыбери действие:", parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "net:create")
async def net_create(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    room_code = generate_code()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM games WHERE player_x = ? AND status = 'waiting'", (user_id,))
    cursor.execute("INSERT INTO games (room_code, player_x, player_o, board, turn, status) VALUES (?, ?, ?, ?, ?, ?)", (room_code, user_id, None, " " * 9, "X", "waiting"))
    conn.commit()
    conn.close()
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Отмена", callback_data="menu:tictactoe")
    await callback.message.edit_text(f"✅ Комната создана!\n\nТвой код: <code>{room_code}</code>\n\nОтправь его другу. Он должен нажать «Войти в комнату» и ввести этот код.\n\nЖдём второго игрока...", parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "net:join")
async def net_join_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    waiting_for_code[user_id] = "tictactoe"
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Отмена", callback_data="menu:tictactoe")
    await callback.message.edit_text("🔑 <b>Вход в комнату</b>\n\nПросто напиши в чат 4-значный код комнаты (например: <code>A1B2</code>):", parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()

def find_winning_move(board, symbol):
    for a, b, c in WIN_CONDITIONS:
        line = [board[a], board[b], board[c]]
        if line.count(symbol) == 2 and line.count(" ") == 1: return [a, b, c][line.index(" ")]
    return None

def bot_move_logic(board, bot_symbol, player_symbol):
    move = find_winning_move(board, bot_symbol)
    if move is not None: return move
    move = find_winning_move(board, player_symbol)
    if move is not None: return move
    if board[4] == " ": return 4
    for i in [0, 2, 6, 8]:
        if board[i] == " ": return i
    for i in range(9):
        if board[i] == " ": return i
    return None

def get_bot_score(user_id):
    return bot_scores.setdefault(user_id, {"wins": 0, "losses": 0, "draws": 0})

def format_score(score):
    return f"📊 Счёт: ты {score['wins']} : {score['losses']} бот (ничьих: {score['draws']})"

@dp.callback_query(F.data.startswith("side:"))
async def choose_side(callback: types.CallbackQuery):
    side = callback.data.split(":")[1]
    user_id = callback.from_user.id
    board = [" "] * 9
    bot_games[user_id] = {"board": board, "player": side, "bot": "O" if side == "X" else "X"}
    game = bot_games[user_id]
    player_sym = symbol_to_text(game["player"])
    await callback.message.edit_text(f"🎮 <b>Игра с ботом</b>\n\nТы играешь за {player_sym}. Твой ход:", parse_mode="HTML", reply_markup=get_bot_board_keyboard(board, user_id))
    if game["player"] == "O":
        async with ChatActionSender.typing(bot=bot, chat_id=user_id):
            await asyncio.sleep(1.0)
            move = bot_move_logic(board, "X", "O")
            board[move] = "X"
        await callback.message.edit_text(f"🎮 <b>Игра с ботом</b>\n\nТы играешь за {O}. Бот сходил {X}. Твой ход:", parse_mode="HTML", reply_markup=get_bot_board_keyboard(board, user_id))
    await callback.answer()

@dp.callback_query(F.data.startswith("botmove:"))
async def handle_bot_move(callback: types.CallbackQuery):
    _, game_id, index = callback.data.split(":")
    game_id = int(game_id); index = int(index)
    if game_id not in bot_games: await callback.answer("Игра не найдена. Напиши /start"); return
    game = bot_games[game_id]
    board = game["board"]; player = game["player"]; bot_sym = game["bot"]
    if board[index] != " ": await callback.answer("Эта клетка уже занята!"); return
    board[index] = player
    score = get_bot_score(game_id)
    await callback.message.edit_reply_markup(reply_markup=get_bot_board_keyboard(board, game_id))
    if check_winner(board, player):
        score["wins"] += 1
        await callback.message.edit_text(f"🎉 Ты победил!\n\n{format_score(score)}\n\nНапиши /start чтобы сыграть ещё.")
        del bot_games[game_id]; await callback.answer(); return
    if " " not in board:
        score["draws"] += 1
        await callback.message.edit_text(f"🤝 Ничья!\n\n{format_score(score)}\n\nНапиши /start чтобы сыграть ещё.")
        del bot_games[game_id]; await callback.answer(); return
    async with ChatActionSender.typing(bot=bot, chat_id=game_id):
        await asyncio.sleep(1.0)
        move = bot_move_logic(board, bot_sym, player)
        board[move] = bot_sym
    if check_winner(board, bot_sym):
        score["losses"] += 1
        await callback.message.edit_text(f"😢 Победил бот ({symbol_to_text(bot_sym)}).\n\n{format_score(score)}\n\nНапиши /start чтобы сыграть ещё.")
        del bot_games[game_id]; await callback.answer(); return
    if " " not in board:
        score["draws"] += 1
        await callback.message.edit_text(f"🤝 Ничья!\n\n{format_score(score)}\n\nНапиши /start чтобы сыграть ещё.")
        del bot_games[game_id]; await callback.answer(); return
    await callback.message.edit_reply_markup(reply_markup=get_bot_board_keyboard(board, game_id))
    await callback.answer()

@dp.callback_query(F.data.startswith("netmove:"))
async def handle_net_move(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    room_code = parts[1]; index = int(parts[2]); user_id = callback.from_user.id
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM games WHERE room_code = ?", (room_code,))
    row = cursor.fetchone()
    if not row: conn.close(); await callback.answer("Игра не найдена."); return
    (_, player_x, player_o, board_str, turn, status, msg_x, msg_o, score_x, score_o) = row
    board = list(board_str)
    if status != "playing": conn.close(); await callback.answer("Игра ещё не началась или уже закончилась."); return
    if user_id == player_x: player_symbol = "X"
    elif user_id == player_o: player_symbol = "O"
    else: conn.close(); await callback.answer("Ты не участвуешь в этой игре."); return
    if turn != player_symbol: conn.close(); await callback.answer("Сейчас не твой ход!"); return
    if board[index] != " ": conn.close(); await callback.answer("Эта клетка уже занята!"); return
    board[index] = player_symbol
    game_over = False; winner_text = ""
    if check_winner(board, player_symbol):
        game_over = True
        if player_symbol == "X": score_x += 1
        else: score_o += 1
        winner_text = f"🎉 Победил {symbol_to_text(player_symbol)}!"
    elif " " not in board:
        game_over = True; winner_text = "🤝 Ничья!"
    if game_over:
        score_text = f"📊 Счёт: {X} {score_x} : {score_o} {O}\n\n{winner_text}"
        cursor.execute("UPDATE games SET status = ?, board = ?, score_x = ?, score_o = ? WHERE room_code = ?", ("finished", "".join(board), score_x, score_o, room_code))
        conn.commit(); conn.close()
        try: await bot.edit_message_text(score_text, chat_id=player_x, message_id=msg_x, reply_markup=get_rematch_keyboard(room_code))
        except Exception: pass
        try: await bot.edit_message_text(score_text, chat_id=player_o, message_id=msg_o)
        except Exception: pass
        await callback.answer(); return
    next_turn = "O" if player_symbol == "X" else "X"
    cursor.execute("UPDATE games SET board = ?, turn = ? WHERE room_code = ?", ("".join(board), next_turn, room_code))
    conn.commit(); conn.close()
    await callback.message.edit_reply_markup(reply_markup=get_net_board_keyboard(board, room_code))
    other_id = player_o if user_id == player_x else player_x
    other_msg_id = msg_o if user_id == player_x else msg_x
    try: await bot.edit_message_text(f"🎮 Твой ход ({symbol_to_text(next_turn)}):", chat_id=other_id, message_id=other_msg_id, reply_markup=get_net_board_keyboard(board, room_code))
    except Exception: pass
    await callback.answer()

@dp.callback_query(F.data.startswith("rematch:"))
async def offer_rematch(callback: types.CallbackQuery):
    room_code = callback.data.split(":")[1]; user_id = callback.from_user.id
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM games WHERE room_code = ?", (room_code,))
    row = cursor.fetchone()
    if not row: conn.close(); await callback.answer("Игра не найдена."); return
    (_, player_x, player_o, board_str, turn, status, msg_x, msg_o, score_x, score_o) = row
    board = [" "] * 9
    cursor.execute("UPDATE games SET board = ?, turn = ?, status = ? WHERE room_code = ?", (" " * 9, "X", "playing", room_code))
    conn.commit(); conn.close()
    await callback.message.edit_text(f"🎮 Реванш начался!\n\nТы играешь за {X}. Твой ход:", reply_markup=get_net_board_keyboard(board, room_code))
    try: await bot.edit_message_text(f"🎮 Реванш начался!\n\nТы играешь за {O}.\nТвой ход будет после {X}.", chat_id=player_o, message_id=msg_o, reply_markup=get_net_board_keyboard(board, room_code))
    except Exception: pass
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
