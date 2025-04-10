import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")         # Токен бота-управления (@BotFather)
ADMIN_ID = int(os.getenv("ADMIN_ID"))      # Ваш ID в Telegram
API_ID = int(os.getenv("API_ID"))          # Ваш api_id (my.telegram.org)
API_HASH = os.getenv("API_HASH")           # Ваш api_hash
SESSION_STRING = os.getenv("SESSION_STRING")  # Сессия Telethon в виде строки

# Глобальные переменные
waiting_for_message = False
mailing_text = ""

# Бот-управление
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 Бот для рассылки\n"
        "Команды:\n"
        "/mailing - задать текст\n"
        "/send - начать рассылку"
    )

async def ask_mailing_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_for_message
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав!")
        return
    waiting_for_message = True
    await update.message.reply_text("📝 Введите текст рассылки:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_for_message, mailing_text
    if waiting_for_message and update.effective_user.id == ADMIN_ID:
        mailing_text = update.message.text
        waiting_for_message = False
        await update.message.reply_text(f"✅ Текст сохранён. Отправьте /send")

# Рассылка через Telethon
async def send_mailing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав!")
        return

    if not mailing_text:
        await update.message.reply_text("❌ Текст не задан!")
        return

    try:
        # Подключаемся к аккаунту рассылки
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            await update.message.reply_text("❌ Ошибка авторизации!")
            return

        # Чтение chat_id из groups.txt
        with open("groups.txt", "r") as file:
            chat_ids = [line.strip() for line in file if line.strip()]

        # Рассылка
        success = 0
        for chat_id in chat_ids:
            try:
                await client.send_message(int(chat_id), mailing_text)
                success += 1
                await asyncio.sleep(2)  # Задержка для избежания флуда
            except Exception as e:
                print(f"Ошибка в чате {chat_id}: {e}")

        await update.message.reply_text(f"📊 Успешно: {success}/{len(chat_ids)}")
        await client.disconnect()

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

if __name__ == "__main__":
    # Бот-управление
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mailing", ask_mailing_text))
    app.add_handler(CommandHandler("send", send_mailing))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()