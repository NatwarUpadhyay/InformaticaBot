"""Minimal Telegram bot for development using python-telegram-bot polling.
Handlers: /ask, /help
"""
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from rag.retriever import Retriever
from rag.generator import generate_answer

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

retriever = Retriever()


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args) if context.args else None
    if not query:
        await update.message.reply_text("Usage: /ask <your question>")
        return

    await update.message.reply_text("Thinking...")
    
    # 1. Retrieve context
    results = retriever.retrieve(query, top_k=3)
    
    if not results:
        await update.message.reply_text("I couldn't find any relevant information to answer your question.")
        return

    # 2. Construct prompt with retrieved context
    context_str = "\n\n".join([f"Source: {r['source']}\nContent: {r['text']}" for r in results])
    prompt = f"""Based on the following context, please answer the user's query.
If the context does not contain the answer, state that you don't know.

Context:
---
{context_str}
---

User Query: {query}
Answer:"""

    # 3. Generate answer
    answer = generate_answer(prompt)
    
    # 4. Send response
    await update.message.reply_text(answer)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/ask <query> - ask the RAG bot\n/help - this help message")


def run_polling():
    if not TOKEN:
        print('Set TELEGRAM_BOT_TOKEN in your environment to run the bot')
        return
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('ask', ask))
    app.add_handler(CommandHandler('help', help_cmd))
    print('Starting polling bot. Press Ctrl-C to stop.')
    app.run_polling()


if __name__ == '__main__':
    run_polling()
