import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Конфигурация (добавьте эти переменные в настройки Vercel)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Ваш ID в Telegram (узнать у @userinfobot)

# Глобальные переменные
waiting_for_message = False
mailing_text = ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📢 Бот для рассылки. Команды:\n/mailing - задать текст\n/send - начать")

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

# Создаем экземпляр бота
app = Application.builder().token(BOT_TOKEN).build()

# Регистрируем обработчики
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("mailing", ask_mailing_text))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# Экспортируем app для Vercel
handler = app.run_webhook  # Ключевая строка для совместимости с Vercel