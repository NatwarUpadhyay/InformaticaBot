"""
Telegram Bot Integration for RAG + Vision Hybrid System
Bot: @InfoMaticaBot
Run this to start the Telegram bot with polling

Token: Set via TELEGRAM_BOT_TOKEN environment variable (see .env.example)
Keep token secure!
"""
import os
import sys
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.bot.handlers import ask_handler, image_handler, photo_handler, help_handler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set!")
    print("   Set it in .env file: TELEGRAM_BOT_TOKEN=your_token_from_botfather")
    print("   Or set it with: export TELEGRAM_BOT_TOKEN='your_token_here'")
    sys.exit(1)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    await update.message.reply_text(
        "👋 **Welcome to InfoMatica Bot!**\n\n"
        "I'm a hybrid RAG + Vision AI assistant. I can:\n\n"
        "🔍 **Answer Questions** - Query our knowledge base\n"
        "📸 **Analyze Images** - Caption and tag images\n\n"
        "**Quick Start:**\n"
        "`/ask What are your features?` - Get instant answers\n"
        "`/image` - Then send me an image to analyze\n\n"
        "Type `/help` for all available commands!"
    )


def main():
    """Start the bot using polling"""
    print("\n" + "="*80)
    print("🚀 Starting InfoMatica Telegram Bot")
    print("="*80)
    print(f"Bot: @InfoMaticaBot")
    print(f"Token: {TELEGRAM_BOT_TOKEN[:20]}...")
    print(f"Status: Connecting to Telegram...")
    print("="*80)
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("ask", ask_handler))
    application.add_handler(CommandHandler("image", image_handler))

    # Register message handlers (photos)
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # Start polling
    print("\n✅ Bot connected successfully!")
    print("✓ Listening for messages on @InfoMaticaBot")
    print("✓ Features: RAG Q&A + Image Analysis")
    print("\nPress Ctrl+C to stop the bot.\n")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
