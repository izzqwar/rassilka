import os
import asyncio
import random
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 5015543786  # Замените на ваш ID из @userinfobot

waiting_for_message = False
mailing_text = ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 Бот для рассылки\n"
        "Команды:\n"
        "/mailing - задать текст рассылки\n"
        "/send - начать рассылку"
    )

async def ask_mailing_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_for_message
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    waiting_for_message = True
    await update.message.reply_text("📝 Введите текст рассылки:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_for_message, mailing_text
    
    if waiting_for_message and update.effective_user.id == ADMIN_ID:
        mailing_text = update.message.text
        waiting_for_message = False
        await update.message.reply_text(
            f"✅ Текст сохранён:\n\n{mailing_text}\n\n"
            "Отправьте /send для начала рассылки"
        )

async def send_mailing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    if not mailing_text:
        await update.message.reply_text("❌ Текст рассылки не задан!")
        return
    
    try:
        with open("groups.txt", "r") as file:
            chat_ids = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        await update.message.reply_text("❌ Файл groups.txt не найден!")
        return
    
    bot = Bot(token=TOKEN)
    success = 0
    failed = 0
    
    await update.message.reply_text(f"🚀 Начинаю рассылку для {len(chat_ids)} чатов...")
    
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=mailing_text)
            success += 1
            await asyncio.sleep(random.uniform(1, 3))  # Задержка 1-3 сек
        except Exception as e:
            failed += 1
            print(f"Ошибка в чате {chat_id}: {e}")
    
    await update.message.reply_text(
        f"📊 Рассылка завершена:\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибки: {failed}"
    )

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mailing", ask_mailing_text))
    app.add_handler(CommandHandler("send", send_mailing))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()
