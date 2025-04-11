import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession

# Конфигурация (из секретов GitHub)
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Создаем папку для сессии
os.makedirs("sessions", exist_ok=True)

# Состояния пользователей
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *Бот для рассылки*\n"
        "🔹 /auth - Авторизовать аккаунт для рассылки\n"
        "🔹 /mailing - Начать рассылку\n\n"
        "ℹ️ ID чатов берутся из файла `groups.txt`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    user_states[update.effective_user.id] = {"step": "waiting_phone"}
    await update.message.reply_text("📱 Отправьте номер телефона в формате +79991234567:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    state = user_states.get(user_id, {})

    # Обработка авторизации
    if state.get("step") == "waiting_phone":
        user_states[user_id] = {
            "step": "waiting_code",
            "phone": update.message.text
        }
        await update.message.reply_text("🔢 Отправьте код из SMS:")
    
    elif state.get("step") == "waiting_code":
        try:
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.start(
                phone=user_states[user_id]["phone"],
                code=lambda: update.message.text
            )
            
            with open("sessions/session.txt", "w") as f:
                f.write(client.session.save())
            
            await update.message.reply_text("✅ Авторизация успешна!")
            user_states.pop(user_id)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    # Обработка рассылки
    elif state.get("step") == "waiting_mailing_text":
        try:
            # Читаем ID чатов из файла
            with open("groups.txt", "r") as f:
                chat_ids = [line.strip() for line in f if line.strip()]
            
            if not chat_ids:
                await update.message.reply_text("⚠️ Файл groups.txt пуст")
                return
            
            # Подключаемся через сохраненную сессию
            with open("sessions/session.txt", "r") as f:
                session_str = f.read().strip()
            
            async with TelegramClient(StringSession(session_str), API_ID, API_HASH) as client:
                success = 0
                for chat_id in chat_ids:
                    try:
                        await client.send_message(int(chat_id), update.message.text)
                        success += 1
                        await asyncio.sleep(2)  # Задержка против флуда
                    except Exception as e:
                        print(f"Ошибка в чате {chat_id}: {e}")
                
                await update.message.reply_text(
                    f"📊 Результат:\n"
                    f"• Успешно: {success}/{len(chat_ids)}\n"
                    f"• Текст: `{update.message.text}`",
                    parse_mode="Markdown"
                )
        
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        
        user_states.pop(user_id)

async def mailing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not os.path.exists("sessions/session.txt"):
        await update.message.reply_text("⚠️ Сначала выполните /auth")
        return
    
    user_states[update.effective_user.id] = {"step": "waiting_mailing_text"}
    await update.message.reply_text("📝 Введите текст рассылки:")

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", auth))
    app.add_handler(CommandHandler("mailing", mailing))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()