import os
import pandas as pd
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from telegram.ext import MessageHandler, filters

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

# Load question data
questions_df = pd.read_csv("Kysymyspaketti.csv", encoding="latin1")
user_states = {}

# Flask app
flask_app = Flask(__name__)

# Telegram bot app
app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = 0
    await update.message.reply_text("Tervetuloa koekysymysbottiin! Kirjoita /kysymys aloittaaksesi.")

async def kysymys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    index = user_states.get(user_id, 0)

    if index >= len(questions_df):
        await update.message.reply_text("Olet käynyt kaikki kysymykset läpi!")
        return

    question = questions_df.iloc[index]["Question"]
    keyboard = [
        [InlineKeyboardButton("TOSI", callback_data="TOSI"),
         InlineKeyboardButton("EPÄTOSI", callback_data="EPÄTOSI")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f"Kysymys {index + 1}:\n{question}", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_answer = query.data
    index = user_states.get(user_id, 0)

    if index >= len(questions_df):
        await context.bot.send_message(chat_id=user_id, text="Olet käynyt kaikki kysymykset läpi!")
        return

    correct_answer = questions_df.iloc[index]["Answer"].strip().upper()
    explanation = questions_df.iloc[index]["Explanation"]
    citation = questions_df.iloc[index]["Citation"]

    result = "✅ Oikein!" if user_answer == correct_answer else f"❌ Väärin! Oikea vastaus oli {correct_answer}."
    await context.bot.send_message(chat_id=user_id, text=f"{result}\n\nSelitys: {explanation}\nLähde: {citation}")

    user_states[user_id] = index + 1

    if user_states[user_id] < len(questions_df):
        next_question = questions_df.iloc[user_states[user_id]]["Question"]
        keyboard = [
            [InlineKeyboardButton("TOSI", callback_data="TOSI"),
             InlineKeyboardButton("EPÄTOSI", callback_data="EPÄTOSI")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Kysymys {user_states[user_id] + 1}:\n{next_question}",
            reply_markup=reply_markup
        )
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Message received:", update.message.text)
    await update.message.reply_text("✅ Bot is alive and got your message!")

# Register handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("kysymys", kysymys))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.ALL, echo))

# Webhook route
@flask_app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    print("Webhook called:", request.get_json(force=True))
    app.update_queue.put_nowait(update)
    return "OK"

# Start everything
if __name__ == "__main__":
    import asyncio
    import threading

    async def main():
        await app.bot.set_webhook(url=WEBHOOK_URL)
        await app.initialize()
        await app.start()
        await app.updater.start_polling()

    def run_flask():
        flask_app.run(host="0.0.0.0", port=10000)

    # Start Flask in its own thread
    threading.Thread(target=run_flask).start()

    # Start the bot in the main thread
    asyncio.run(main())
