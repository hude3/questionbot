import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")  # e.g., https://koekysymysbotti.onrender.com
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"


# Load questions at startup
questions_df = pd.read_csv("Kysymyspaketti.csv", encoding="latin1")

# Track user progress
user_states = {}

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
        [
            InlineKeyboardButton("TOSI", callback_data="TOSI"),
            InlineKeyboardButton("EPÄTOSI", callback_data="EPÄTOSI"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
    f"Kysymys {index + 1}:\n{question}",
    reply_markup=reply_markup
)

# Handle user answer
"""
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_answer = update.message.text.strip().upper()
    index = user_states.get(user_id, 0)

    if index >= len(questions_df):
        return

    correct_answer = questions_df.iloc[index]["Answer"].strip().upper()
    explanation = questions_df.iloc[index]["Explanation"]
    citation = questions_df.iloc[index]["Citation"]

    if user_answer in ["TOSI", "EPÄTOSI"]:
        if user_answer == correct_answer:
            reply = "✅ Oikein!"
        else:
            reply = f"❌ Väärin! Oikea vastaus oli {correct_answer}."

        reply += f"\n\nSelitys: {explanation}\nLähde: {citation}"
        await update.message.reply_text(reply)

        # Move to next question
        user_states[user_id] = index + 1
    else:
        await update.message.reply_text("Vastaa vain 'TOSI' tai 'EPÄTOSI'.")
"""
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_answer = query.data
    index = user_states.get(user_id, 0)

    if index == -1:
        await context.bot.send_message(chat_id=user_id, text="Olet lopettanut kyselysession. Kirjoita /start aloittaaksesi uudelleen.")
        return

    if index >= len(questions_df):
        await context.bot.send_message(chat_id=user_id, text="Olet käynyt kaikki kysymykset läpi!")
        return

    correct_answer = questions_df.iloc[index]["Answer"].strip().upper()
    explanation = questions_df.iloc[index]["Explanation"]
    citation = questions_df.iloc[index]["Citation"]

    if user_answer == correct_answer:
        result = "✅ Oikein!"
    else:
        result = f"❌ Väärin! Oikea vastaus oli {correct_answer}."

    response = f"{result}\n\nSelitys: {explanation}\nLähde: {citation}"

    # Send result without deleting the original question
    await context.bot.send_message(chat_id=user_id, text=response)

    # Move to next question
    user_states[user_id] = index + 1

    # Ask next question automatically
    if user_states[user_id] < len(questions_df):
        next_index = user_states[user_id]
        next_question = questions_df.iloc[next_index]["Question"]

        keyboard = [
            [
                InlineKeyboardButton("TOSI", callback_data="TOSI"),
                InlineKeyboardButton("EPÄTOSI", callback_data="EPÄTOSI"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"\nKysymys {next_index + 1}:\n{next_question}",
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(chat_id=user_id, text="Olet käynyt kaikki kysymykset läpi!")

async def lopeta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Remove the user’s state completely
    if user_id in user_states:
        del user_states[user_id]

    await update.message.reply_text(
        "Olet lopettanut kyselysession. Kirjoita /start aloittaaksesi uudelleen."
    )

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("kysymys", kysymys))
app.add_handler(CommandHandler("lopeta", lopeta))
app.add_handler(CallbackQueryHandler(button_handler))

@flask_app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    await app.update_queue.put(update)
    return "OK"


if __name__ == "__main__":
    import asyncio

    async def main():
        await app.bot.set_webhook(url=WEBHOOK_URL)
        app.run_webhook(
            listen="0.0.0.0",
            port=10000,
            webhook_url=WEBHOOK_URL,
            flask_app=flask_app
        )

    asyncio.run(main())
