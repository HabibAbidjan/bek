from keep_alive import keep_alive
import telebot
from telebot import types
import random
import threading
import time
import datetime

TOKEN = "8161107014:AAH1I0srDbneOppDw4AsE2kEYtNtk7CRjOw"
bot = telebot.TeleBot(TOKEN)

user_balances = {}
user_games = {}
user_aviator = {}
user_bonus_state = {}  # Kunlik bonus holati
ADMIN_ID = 5815294733

# === /addbal komandasi (admin uchun) ===
addbal_state = {}

@bot.message_handler(commands=['addbal'])
def addbal_step1(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Sizda bu buyruqdan foydalanishga ruxsat yo‘q.")
        return
    msg = bot.send_message(message.chat.id, "👤 Foydalanuvchi ID sini kiriting:")
    bot.register_next_step_handler(msg, addbal_step2)

def addbal_step2(message):
    try:
        user_id = int(message.text)
        addbal_state[message.chat.id] = {'target_id': user_id}
        msg = bot.send_message(message.chat.id, "💰 Qo‘shiladigan summani kiriting:")
        bot.register_next_step_handler(msg, addbal_step3)
    except ValueError:
        bot.send_message(message.chat.id, "❌ ID faqat raqam bo‘lishi kerak.")

def addbal_step3(message):
    try:
        chat_id = message.chat.id
        amount = int(message.text)
        target_id = addbal_state[chat_id]['target_id']

        user_balances[target_id] = user_balances.get(target_id, 0) + amount
        bot.send_message(chat_id, f"✅ {target_id} hisobiga {amount} so‘m qo‘shildi.")

        try:
            bot.send_message(target_id, f"💰 Hisobingizga {amount} so‘m qo‘shildi. Yangi balans: {user_balances[target_id]} so‘m")
        except Exception:
            pass

        del addbal_state[chat_id]
    except ValueError:
        bot.send_message(message.chat.id, "❌ Summani faqat raqam bilan kiriting.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Xatolik: {str(e)}")

# === /start komandasi + REFERAL ===
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    # REFERAL LINK
    if len(message.text.split()) > 1:
        referrer_id = int(message.text.split()[1])
        if user_id != referrer_id:
            if user_id not in user_balances:
                user_balances[user_id] = 1000
                user_balances[referrer_id] = user_balances.get(referrer_id, 0) + 2000
                try:
                    bot.send_message(referrer_id, f"🎉 Siz do‘stingizni taklif qildingiz! +2000 so‘m")
                except:
                    pass
    else:
        user_balances.setdefault(user_id, 1000)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('💣 Play Mines', '🛩 Play Aviator')
    markup.add('🎲 Play Dice', '💰 Balance')
    markup.add('💸 Pul chiqarish', '💳 Hisob toldirish')
    markup.add('🎁 Kunlik bonus', '📨 Referal link')
    bot.send_message(message.chat.id, "Xush kelibsiz! O'yinni tanlang:", reply_markup=markup)

# === 💣 Mines Game ===
@bot.message_handler(func=lambda m: m.text == "💣 Play Mines")
def start_mines(message):
    user_id = message.from_user.id
    if user_id in user_games:
        bot.send_message(message.chat.id, "❗ Sizda davom etayotgan o‘yin bor. Avval yakunlang.")
        return
    msg = bot.send_message(message.chat.id, "🎯 Stavka miqdorini kiriting (min 1000 so‘m):")
    bot.register_next_step_handler(msg, init_mines)

def init_mines(message):
    try:
        user_id = message.from_user.id
        stake = int(message.text)
        if stake < 1000:
            bot.send_message(message.chat.id, "❌ Kamida 1000 so‘m tikish kerak.")
            return
        if user_balances.get(user_id, 0) < stake:
            bot.send_message(message.chat.id, "❌ Hisobingizda mablag‘ yetarli emas.")
            return

        user_balances[user_id] -= stake
        bombs = random.sample(range(25), 3)
        user_games[user_id] = {
            'stake': stake,
            'bombs': bombs,
            'opened': [],
            'multiplier': 1.0
        }
        send_mines_board(message.chat.id, user_id, bomb_triggered=False)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Raqam kiritish kerak.")

def send_mines_board(chat_id, user_id, bomb_triggered=False):
    game = user_games.get(user_id)
    if not game:
        return

    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = []

    for i in range(25):
        if i in game['opened']:
            if i in game['bombs'] and bomb_triggered:
                btn = types.InlineKeyboardButton("💥", callback_data="ignore")
            else:
                btn = types.InlineKeyboardButton("✅", callback_data="ignore")
        else:
            btn = types.InlineKeyboardButton(str(i + 1), callback_data=f"open_{i}")
        buttons.append(btn)

    for i in range(0, 25, 5):
        markup.row(*buttons[i:i + 5])

    if not bomb_triggered:
        markup.add(types.InlineKeyboardButton("💸 Pulni yechish", callback_data="cashout"))

    text = f"""💣 MINES O'yini

🔢 Bombalar: 3
💰 Stavka: {game['stake']} so‘m
📈 Multiplikator: x{round(game['multiplier'], 2)}
"""
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("open_") or call.data == "cashout")
def handle_mines_callback(call):
    user_id = call.from_user.id
    if user_id not in user_games:
        bot.answer_callback_query(call.id, "⛔ O‘yin topilmadi.")
        return

    game = user_games[user_id]

    if call.data == "cashout":
        win = min(int(game['stake'] * game['multiplier']), int(game['stake'] * 2))
        user_balances[user_id] += win
        del user_games[user_id]
        bot.edit_message_text(f"✅ {win} so‘m yutdingiz! Tabriklaymiz!", call.message.chat.id, call.message.message_id)
        return

    idx = int(call.data.split("_")[1])
    if idx in game['opened']:
        bot.answer_callback_query(call.id, "Bu katak allaqachon ochilgan.")
        return

    if idx in game['bombs']:
        game['opened'] = list(set(game['opened'] + game['bombs']))
        send_mines_board(call.message.chat.id, user_id, bomb_triggered=True)
        del user_games[user_id]
        bot.edit_message_text("💥 Bomba topildi! Siz yutqazdingiz.", call.message.chat.id, call.message.message_id)
        return

    game['opened'].append(idx)
    game['multiplier'] *= 1.08
    send_mines_board(call.message.chat.id, user_id, bomb_triggered=False)

# === 🛩 Aviator ===
@bot.message_handler(func=lambda m: m.text == "🛩 Play Aviator")
def play_aviator(message):
    user_id = message.from_user.id

    if user_id in user_aviator:
        bot.send_message(message.chat.id, "⏳ Avvalgi Aviator o‘yini tugamagani uchun kuting.")
        return

    if user_balances.get(user_id, 0) < 1000:
        bot.send_message(message.chat.id, "❌ Kamida 1000 so‘m kerak.")
        return

    msg = bot.send_message(message.chat.id, "🎯 Stavka miqdorini kiriting (min 1000 so‘m):")
    bot.register_next_step_handler(msg, process_aviator_stake)

def process_aviator_stake(message):
    try:
        user_id = message.from_user.id
        stake = int(message.text)

        if stake < 1000:
            bot.send_message(message.chat.id, "❌ Minimal stavka 1000 so‘m.")
            return

        if user_balances.get(user_id, 0) < stake:
            bot.send_message(message.chat.id, "❌ Yetarli balans yo‘q.")
            return

        user_balances[user_id] -= stake
        user_aviator[user_id] = {
            'stake': stake,
            'multiplier': 1.0,
            'chat_id': message.chat.id,
            'message_id': None,
            'stopped': False
        }

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛑 STOP", callback_data="aviator_stop"))

        msg = bot.send_message(message.chat.id, f"🛫 Boshlanmoqda... x1.00", reply_markup=markup)
        user_aviator[user_id]['message_id'] = msg.message_id

        threading.Thread(target=run_aviator_game, args=(user_id,)).start()

    except ValueError:
        bot.send_message(message.chat.id, "❌ Raqam kiriting.")

def run_aviator_game(user_id):
    data = user_aviator.get(user_id)
    if not data:
        return

    chat_id = data['chat_id']
    message_id = data['message_id']
    stake = data['stake']
    multiplier = data['multiplier']

    for _ in range(30):
        if user_aviator.get(user_id, {}).get('stopped'):
            win = int(stake * multiplier)
            user_balances[user_id] += win
            bot.edit_message_text(f"🛑 To‘xtatildi: x{multiplier}\n✅ Yutuq: {win} so‘m", chat_id, message_id)
            del user_aviator[user_id]
            return

        time.sleep(1)
        multiplier = round(multiplier + random.uniform(0.15, 0.4), 2)
        chance = random.random()

        if (multiplier <= 1.6 and chance < 0.3) or (1.6 < multiplier <= 2.4 and chance < 0.15) or (multiplier > 2.4 and chance < 0.1):
            bot.edit_message_text(f"💥 Portladi: x{multiplier}\n❌ Siz yutqazdingiz.", chat_id, message_id)
            del user_aviator[user_id]
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛑 STOP", callback_data="aviator_stop"))
        try:
            bot.edit_message_text(f"🛩 Ko‘tarilmoqda... x{multiplier}", chat_id, message_id, reply_markup=markup)
        except:
            pass

        user_aviator[user_id]['multiplier'] = multiplier

@bot.callback_query_handler(func=lambda call: call.data == "aviator_stop")
def aviator_stop(call):
    user_id = call.from_user.id
    if user_id in user_aviator:
        user_aviator[user_id]['stopped'] = True
        bot.answer_callback_query(call.id, "🛑 O'yin to'xtatildi, pulingiz hisobingizga qo'shildi.")

# === Kunlik bonus ===
@bot.message_handler(func=lambda m: m.text == "🎁 Kunlik bonus")
def daily_bonus_text(message):
    user_id = message.from_user.id
    today = datetime.date.today()
    last_bonus_date = user_bonus_state.get(user_id)

    if last_bonus_date == today:
        bot.send_message(message.chat.id, "🎁 Siz bugun allaqachon bonus oldingiz. Ertaga yana keling!")
        return

    bonus = random.randint(1000, 5000)
    user_balances[user_id] = user_balances.get(user_id, 0) + bonus
    user_bonus_state[user_id] = today
    bot.send_message(message.chat.id, f"🎉 Tabriklaymiz! Sizga {bonus} so‘m bonus berildi!")

print("Bot ishga tushdi...")
keep_alive()
bot.polling(none_stop=True)
