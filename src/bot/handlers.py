from telegram import Update
from telegram.ext import ContextTypes
from src.rag.retriever import retrieve
from src.rag.generator import generate
from src.vision.captioner import caption_image
import io

async def ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /ask <question> - Query the RAG knowledge base"""
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text(
            "📚 **Usage:** `/ask <your question>`\n\n"
            "Example: `/ask What features do you offer?`"
        )
        return

    await update.message.reply_text("🔍 Searching knowledge base...")

    try:
        chunks = retrieve(query, top_k=3)
        
        if not chunks:
            await update.message.reply_text("❌ No relevant information found in knowledge base.")
            return
        
        answer = generate(query, chunks, use_ollama=True)

        sources = list(set(c["source"] for c in chunks))
        source_line = f"\n\n📚 **Sources**: {', '.join(sources)}" if sources else ""

        await update.message.reply_text(answer + source_line)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /image command - expect user to send an image"""
    await update.message.reply_text(
        "📸 **Image Description Mode**\n\n"
        "Please send me an image and I will:\n"
        "• Generate a detailed description\n"
        "• Extract 3 key tags\n\n"
        "Just upload/send the image in the next message!"
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle actual photo uploads - Generate captions and tags"""
    try:
        # Get the largest version of the photo
        photo_file = await update.message.photo[-1].get_file()
        
        # Download image as bytes
        image_bytes = await photo_file.download_as_bytearray()
        image_bytes = bytes(image_bytes)
        
        await update.message.reply_text("🤖 Analyzing image...")
        
        # Generate caption and tags using vision API
        result = caption_image(image_bytes, use_local=False)
        
        # Format response
        caption = result.get('caption', 'Unable to generate caption')
        tags = result.get('tags', [])
        
        response_text = (
            f"📸 **Image Analysis**\n\n"
            f"**Caption:** {caption}\n\n"
            f"**Tags:** {', '.join(tags) if tags else 'No tags'}"
        )
        
        await update.message.reply_text(response_text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing image: {str(e)}")

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command"""
    await update.message.reply_text(
        "🤖 **InfoMatica Bot - Help Guide**\n\n"
        "**📚 Available Commands:**\n\n"
        "🔍 **`/ask <question>`**\n"
        "   Query the knowledge base for instant answers\n"
        "   Example: `/ask What features do you offer?`\n\n"
        "📸 **`/image`**\n"
        "   Analyze images - I'll caption and tag them\n"
        "   Usage: Type `/image` then send an image\n\n"
        "❓ **`/help`**\n"
        "   Show this help message\n\n"
        "**✨ Capabilities:**\n"
        "• Fast answers from our knowledge base\n"
        "• AI-powered image analysis\n"
        "• Source citations for all answers\n"
        "• Local Ollama + Vision API integration\n\n"
        "**🔧 Tech Stack:**\n"
        "• RAG: Ollama (llama3.2:1b)\n"
        "• Vision: OpenRouter API\n"
        "• Retrieval: Semantic search\n\n"
        "_Need support? Contact @BotSupport_"
    )

