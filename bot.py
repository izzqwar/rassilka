import os
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telethon import TelegramClient
from telethon.sessions import StringSession

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_FILE = "session.session"

# Состояния для ConversationHandler
PHONE, CODE, TFA = range(3)

# Инициализация клиента Telethon
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

async def start_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск процесса аутентификации"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещен.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🔑 Введите номер телефона (в формате +79991234567):"
    )
    return PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка номера телефона"""
    context.user_data["phone"] = update.message.text
    await client.connect()
    try:
        await client.send_code_request(context.user_data["phone"])
        await update.message.reply_text("📲 Код подтверждения отправлен. Введите код:")
        return CODE
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return ConversationHandler.END

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кода подтверждения"""
    code = update.message.text.strip()
    try:
        await client.sign_in(
            phone=context.user_data["phone"],
            code=code
        )
        await update.message.reply_text("✅ Успешная авторизация!")
        await client.disconnect()
    except Exception as e:
        if "two-step verification" in str(e):
            await update.message.reply_text("🔐 Введите пароль двухфакторной аутентификации:")
            return TFA
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return ConversationHandler.END
    return ConversationHandler.END

async def handle_tfa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка двухфакторной аутентификации"""
    password = update.message.text
    try:
        await client.sign_in(password=password)
        await update.message.reply_text("✅ Успешная авторизация!")
        await client.disconnect()
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "🤖 Бот готов к работе. Используйте /auth для авторизации."
    )

async def mailing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик рассылки"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not await client.is_user_authorized():
        await update.message.reply_text("⚠️ Требуется авторизация! Используйте /auth")
        return

    await update.message.reply_text("📝 Введите текст рассылки:")
    context.user_data["state"] = "awaiting_mailing_text"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста рассылки"""
    if context.user_data.get("state") != "awaiting_mailing_text":
        return

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
                    await asyncio.sleep(5)
                except Exception as e:
                    print(f"Ошибка в чате {chat_id}: {e}")

            await update.message.reply_text(
                f"📊 Результат:\n• Успешно: {success}/{len(chat_ids)}"
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    context.user_data.pop("state", None)

def load_chats():
    """Загрузка ID чатов"""
    try:
        with open("groups.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

async def init_client():
    """Инициализация клиента"""
    if os.path.exists(SESSION_FILE):
        await client.start()
        return True
    return False

if __name__ == "__main__":
    # Инициализация бота
    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler для аутентификации
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("auth", start_auth)],
        states={
            PHONE: [MessageHandler(filters.TEXT, handle_phone)],
            CODE: [MessageHandler(filters.TEXT, handle_code)],
            TFA: [MessageHandler(filters.TEXT, handle_tfa)],
        },
        fallbacks=[]
    )

    # Регистрация обработчиков
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mailing", mailing))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск
    app.run_polling()
