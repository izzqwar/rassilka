import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
SESSION_STRING = os.getenv("SESSION_STRING")  # Для инициализации сессии
PING_URL = os.getenv("PING_URL", "")

# Инициализация клиента Telethon
client = TelegramClient(
    StringSession(SESSION_STRING) if SESSION_STRING else "session",
    int(os.getenv("API_ID")),
    os.getenv("API_HASH")
)

async def ping_server():
    """Пинг для поддержания активности"""
    if PING_URL:
        import requests
        try: requests.get(PING_URL)
        except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    chat_count = len(load_chats())
    await update.message.reply_text(
        f"🤖 Бот готов к работе\n"
        f"📊 Чатов в базе: {chat_count}\n"
        f"🔹 /mailing - Начать рассылку",
        parse_mode="Markdown"
    )

def load_chats():
    """Загрузка ID чатов из файла"""
    try:
        with open("groups.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

async def mailing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик рассылки"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    await update.message.reply_text("📝 Введите текст рассылки:")
    context.user_data["state"] = "awaiting_mailing_text"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("state") == "awaiting_mailing_text":
        try:
            chat_ids = load_chats()
            if not chat_ids:
                await update.message.reply_text("⚠️ Файл groups.txt пуст")
                return

            async with client:
                success = 0
                for chat_id in chat_ids:
                    try:
                        await client.send_message(int(chat_id), update.message.text)
                        success += 1
                        await asyncio.sleep(2)
                    except Exception as e:
                        print(f"Ошибка в чате {chat_id}: {e}")

                await update.message.reply_text(
                    f"📊 Результат:\n"
                    f"• Успешно: {success}/{len(chat_ids)}",
                    parse_mode="Markdown"
                )
                await ping_server()

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        
        context.user_data.pop("state", None)

async def connect_client():
    """Подключение клиента Telethon"""
    if not await client.is_user_authorized():
        if SESSION_STRING:
            await client.start()
        else:
            raise Exception("Требуется файл сессии или SESSION_STRING")

if __name__ == "__main__":
    # Инициализация бота
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mailing", mailing))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск
    app.run_polling()