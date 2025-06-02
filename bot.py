import os
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")  # e.g., https://yourbot.onrender.com
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

# Load CSV
questions_df = pd.read_csv("Kysymyspaketti.csv", encoding="latin1")
user_states = {}

# Create app
app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Handlers ---

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
    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f"Kysymys {index + 1}:\n{question}", reply_markup=markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    index = user_states.get(user_id, 0)
    user_answer = query.data

    if index >= len(questions_df):
        await context.bot.send_message(chat_id=user_id, text="Olet käynyt kaikki kysymykset läpi!")
        return

    correct = questions_df.iloc[index]["Answer"].strip().upper()
    explanation = questions_df.iloc[index]["Explanation"]
    citation = questions_df.iloc[index]["Citation"]

    result = "✅ Oikein!" if user_answer == correct else f"❌ Väärin! Oikea vastaus oli {correct}."
    await context.bot.send_message(chat_id=user_id, text=f"{result}\n\nSelitys: {explanation}\nLähde: {citation}")

    user_states[user_id] = index + 1

    if user_states[user_id] < len(questions_df):
        next_q = questions_df.iloc[user_states[user_id]]["Question"]
        keyboard = [
            [InlineKeyboardButton("TOSI", callback_data="TOSI"),
             InlineKeyboardButton("EPÄTOSI", callback_data="EPÄTOSI")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_id,
                                       text=f"Kysymys {user_states[user_id] + 1}:\n{next_q}",
                                       reply_markup=markup)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Message received:", update.message.text)
    await update.message.reply_text("✅ Bot is alive and got your message!")

async def lopeta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Remove the user’s state completely
    if user_id in user_states:
        del user_states[user_id]

    await update.message.reply_text(
        "Olet lopettanut kyselysession. Kirjoita /start aloittaaksesi uudelleen."
    )

# Register handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("kysymys", kysymys))
app.add_handler(CommandHandler("lopeta", lopeta))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.ALL, echo))

# Run webhook (no Flask needed!)
if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL
    )
