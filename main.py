import json
import os
import logging
import random
from telegram import ChatMember
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio
import nest_asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальный путь для хранения данных
DATA_DIR = "bot_data"
WARNINGS_FILE = os.path.join(DATA_DIR, "warnings.json")
MUTES_FILE = os.path.join(DATA_DIR, "mutes.json")
BANS_FILE = os.path.join(DATA_DIR, "bans.json")
DICK_FILE = os.path.join(DATA_DIR, "dick.json")

# Утилита для загрузки данных из JSON
def load_data(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as file:
        return json.load(file)

# Утилита для сохранения данных в JSON
def save_data(file_path, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    return user.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]

# Обработка команды /warn
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        await update.message.reply_text("⛔ У вас недостаточно прав для использования этой команды.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Эту команду нужно использовать в ответ на сообщение.")
        return

    reason = " ".join(context.args) or "Без причины"
    warned_user_id = update.message.reply_to_message.from_user.id
    warned_user_name = update.message.reply_to_message.from_user.full_name
    warned_by = update.message.from_user.full_name

    warnings = load_data(WARNINGS_FILE)
    if str(warned_user_id) not in warnings:
        warnings[str(warned_user_id)] = []

    warnings[str(warned_user_id)].append({
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "warned_by": warned_by
    })

    save_data(WARNINGS_FILE, warnings)

    await update.message.reply_text(f"⚠️ Пользователь {warned_user_name} получил предупреждение. Причина: {reason}")

    # Уведомление в личные сообщения
    try:
        await context.bot.send_message(
            chat_id=warned_user_id,
            text=(f"⚠️ Вас предупредили в группе {update.message.chat.title} \n"
                  f"👤 Выдано: {warned_by}\n"
                  f"📝 Причина: {reason}")
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить сообщение пользователю: {e}")


# Обработка команды /unwarn
async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        await update.message.reply_text("⛔ У вас недостаточно прав для использования этой команды.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Эту команду нужно использовать в ответ на сообщение.")
        return

    warned_user_id = update.message.reply_to_message.from_user.id
    warnings = load_data(WARNINGS_FILE)

    if str(warned_user_id) not in warnings or not warnings[str(warned_user_id)]:
        await update.message.reply_text("ℹ️ У пользователя нет предупреждений.")
        return

    warnings[str(warned_user_id)].pop()
    save_data(WARNINGS_FILE, warnings)
    await update.message.reply_text("✅ Последнее предупреждение снято.")

# Обработка команды /mute
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        await update.message.reply_text("⛔ У вас недостаточно прав для использования этой команды.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Эту команду нужно использовать в ответ на сообщение.")
        return

    try:
        mute_duration = int(context.args[0])
        reason = " ".join(context.args[1:]) or "Без причины"
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /mute <время в минутах> <причина>")
        return

    muted_user_id = update.message.reply_to_message.from_user.id
    mute_end_time = datetime.now() + timedelta(minutes=mute_duration)
    muted_by = update.message.from_user.full_name

    mutes = load_data(MUTES_FILE)
    mutes[str(muted_user_id)] = {
        "until": mute_end_time.isoformat(),
        "reason": reason,
        "muted_by": muted_by
    }
    save_data(MUTES_FILE, mutes)

    await context.bot.restrict_chat_member(
        chat_id=update.message.chat_id,
        user_id=muted_user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=mute_end_time
    )

    await update.message.reply_text(f"🔇 Пользователь был заглушен на {mute_duration} минут. Причина: {reason}")

    # Уведомление в личные сообщения
    try:
        await context.bot.send_message(
            chat_id=muted_user_id,
            text=(f"🔇 Вас заглушили в группе {update.message.chat.title}\n"
                  f"👤 Выдано: {muted_by}\n"
                  f"⏱️ На время: {mute_duration} минут\n"
                  f"📝 Причина: {reason}")
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить сообщение пользователю: {e}")


# Обработка команды /unmute
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        await update.message.reply_text("⛔ У вас недостаточно прав для использования этой команды.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Эту команду нужно использовать в ответ на сообщение.")
        return

    unmuted_user_id = update.message.reply_to_message.from_user.id
    mutes = load_data(MUTES_FILE)

    if str(unmuted_user_id) in mutes:
        del mutes[str(unmuted_user_id)]
        save_data(MUTES_FILE, mutes)

    await context.bot.restrict_chat_member(
        chat_id=update.message.chat_id,
        user_id=unmuted_user_id,
        permissions=ChatPermissions(can_send_messages=True)
    )

    await update.message.reply_text("✅ Пользователь был размучен.")

# Обработка команды /ban
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        await update.message.reply_text("⛔ У вас недостаточно прав для использования этой команды.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Эту команду нужно использовать в ответ на сообщение.")
        return

    reason = " ".join(context.args) or "Без причины"
    banned_user_id = update.message.reply_to_message.from_user.id
    banned_by = update.message.from_user.full_name

    bans = load_data(BANS_FILE)
    bans[str(banned_user_id)] = {
        "reason": reason,
        "banned_by": banned_by,
        "timestamp": datetime.now().isoformat()
    }
    save_data(BANS_FILE, bans)

    await context.bot.ban_chat_member(
        chat_id=update.message.chat_id,
        user_id=banned_user_id
    )

    await update.message.reply_text(f"⛔ Пользователь был забанен. Причина: {reason}")

    # Уведомление в личные сообщения
    try:
        await context.bot.send_message(
            chat_id=banned_user_id,
            text=(f"⛔ Вас забанили в группе {update.message.chat.title}\n"
                  f"👤 Выдано: {banned_by}\n"
                  f"📝 Причина: {reason}")
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить сообщение пользователю: {e}")

# Обработка команды /unban
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        await update.message.reply_text("⛔ У вас недостаточно прав для использования этой команды.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Эту команду нужно использовать в ответ на сообщение.")
        return

    unbanned_user_id = update.message.reply_to_message.from_user.id
    bans = load_data(BANS_FILE)

    if str(unbanned_user_id) in bans:
        del bans[str(unbanned_user_id)]
        save_data(BANS_FILE, bans)

    await context.bot.unban_chat_member(
        chat_id=update.message.chat_id,
        user_id=unbanned_user_id
    )

    await update.message.reply_text("✅ Пользователь был разбанен.")

# Обработка команды /warns
async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user_id = update.message.from_user.id

    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id

    warnings = load_data(WARNINGS_FILE)
    user_warnings = warnings.get(str(target_user_id), [])

    if not user_warnings:
        await update.message.reply_text("ℹ️ У пользователя нет предупреждений.")
        return

    warnings_text = "\n".join([
        f"⚠️ Причина: {w['reason']}, Дата: {w['timestamp']}, Выдано: {w['warned_by']}"
        for w in user_warnings
    ])

    await update.message.reply_text(f"📋 Предупреждения пользователя:\n{warnings_text}")

async def piccolo_dick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_name = update.message.from_user.full_name
    dick_data = load_data(DICK_FILE)

    now = datetime.now()
    if user_id in dick_data:
        last_used = datetime.fromisoformat(dick_data[user_id].get("last_used", "1970-01-01T00:00:00"))
        if (now - last_used).total_seconds() < 86400:
            await update.message.reply_text("⏳ Вы уже использовали эту команду за последние 24 часа. Подождите!")
            return

    change = random.randint(-5, 10)
    current_length = dick_data.get(user_id, {"length": 10}).get("length", 10) + change
    current_length = max(1, current_length)  # Минимальная длина - 1 см

    dick_data[user_id] = {
        "length": current_length,
        "last_used": now.isoformat(),
        "name": user_name
    }

    save_data(DICK_FILE, dick_data)

    sorted_top = sorted(dick_data.items(), key=lambda x: x[1]["length"], reverse=True)
    user_position = next((i for i, x in enumerate(sorted_top, 1) if x[0] == user_id), None)

    await update.message.reply_text(
        f"📏 {user_name}, твой хуй вырос на {change:+} см.\n"
        f"🔢 Сейчас он равен: {current_length} см.\n"
        f"🏆 Ты занимаешь {user_position}-е место в топе."
    )

# Обработка команды /PiccoloDickTop
async def piccolo_dick_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dick_data = load_data(DICK_FILE)

    if not dick_data:
        await update.message.reply_text("ℹ️ Никто ещё не использовал /PiccoloDick.")
        return

    sorted_top = sorted(dick_data.items(), key=lambda x: x[1]["length"], reverse=True)[:10]
    top_text = "🏆 Топ участников группы:\n"

    for i, (user_id, data) in enumerate(sorted_top, 1):
        top_text += f"{i}. {data['name']} — {data['length']} см\n"

    await update.message.reply_text(top_text)



# Основная функция запуска бота
async def main():
    application = ApplicationBuilder().token("7836059868:AAGr6pjGpIT1MPtADqTLxaP3Oo7Him4y6DQ").build()

    application.add_handler(CommandHandler("warn", warn))
    application.add_handler(CommandHandler("unwarn", unwarn))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("warns", warns))
    application.add_handler(CommandHandler("dick", piccolo_dick))
    application.add_handler(CommandHandler("dicktop", piccolo_dick_top))

    await application.initialize()

    try:
        await application.run_polling()
    finally:
        await application.shutdown()

if __name__ == "__main__":
    nest_asyncio.apply()
    try:
        asyncio.run(main())
    except RuntimeError as e:
        logger.error(f"Ошибка при запуске бота: {e}")