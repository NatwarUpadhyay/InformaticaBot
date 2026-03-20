import gradio as gr
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.retriever import retrieve
from src.rag.generator import generate
from src.vision.captioner import caption_image

# Default model sources
text_use_ollama = True  # Use Ollama by default (local)
vision_use_local = False

def chat_fn(message, history, text_source):
    """Chat interface for RAG queries"""
    global text_use_ollama
    text_use_ollama = text_source == "Local Model (Ollama)"
    
    chunks = retrieve(message, top_k=3)
    answer = generate(message, chunks, use_ollama=text_use_ollama)
    sources = list(set(c["source"] for c in chunks))
    if sources:
        answer += f"\n\n**📚 Sources**: {', '.join(sources)}"
    return answer

def image_upload_fn(image, vision_source):
    """Process uploaded image for vision"""
    import io
    global vision_use_local
    vision_use_local = vision_source == "Local Model"
    
    if image is None:
        return "Please upload an image first.", ""
    
    # Convert to bytes
    if isinstance(image, str):
        # Gradio returns file path as string
        with open(image, 'rb') as f:
            image_bytes = f.read()
    else:
        # If it's PIL Image
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        image_bytes = buf.getvalue()
    
    result = caption_image(image_bytes, use_local=vision_use_local)
    caption = result.get('caption', 'No caption generated')
    tags = ", ".join(result.get('tags', []))
    
    output = f"**Caption:** {caption}\n\n**Tags:** {tags}"
    return output, image

def build_gradio_ui():
    """Build Gradio UI for testing/debugging the hybrid RAG + Vision bot"""
    with gr.Blocks(title="Hybrid Bot - Debug Interface") as demo:
        gr.Markdown("""
        # 🤖 Hybrid Bot (RAG + Vision) - Debug Interface
        
        This is a **testing/debugging interface** for the hybrid bot supporting both text and image modes.
        
        **Primary interface**: Use the Telegram bot (`t.me/InfoMaticaBot`) for the actual experience.
        
        This UI is useful for:
        - Testing text Q&A (RAG mode)
        - Testing image captioning (Vision mode)
        - Verifying document retrieval and vision model responses
        """)
        
        with gr.Tab("💬 Chat (RAG Mode)"):
            gr.Markdown("### Text Q&A using RAG")
            with gr.Row():
                text_source_radio = gr.Radio(
                    choices=["OpenRouter API (GPT-3.5)", "Local Model (Ollama)"],
                    value="Local Model (Ollama)",
                    label="🤖 Text Model Source",
                    info="Choose between cloud API or local Ollama (default: local, faster & free)"
                )
            gr.ChatInterface(
                fn=chat_fn, 
                additional_inputs=[text_source_radio],
                examples=[
                    ["What are the main features?", "Local Model (Ollama)"],
                    ["How does the system work?", "Local Model (Ollama)"],
                    ["What is the significance of this paper?", "OpenRouter API"]
                ]
            )
        
        with gr.Tab("📸 Image Description (Vision Mode)"):
            gr.Markdown("### Image Captioning & Tag Extraction")
            with gr.Row():
                vision_source_radio = gr.Radio(
                    choices=["OpenRouter API (Mistral)", "Local Model (BLIP)"],
                    value="OpenRouter API (Mistral)",
                    label="🤖 Vision Model Source",
                    info="Choose between cloud API (better quality) or local model (offline)"
                )
            with gr.Row():
                with gr.Column():
                    image_input = gr.Image(label="Upload Image", type="filepath")
                with gr.Column():
                    image_output = gr.Textbox(label="Description & Tags", lines=6)
            
            image_input.change(fn=image_upload_fn, inputs=[image_input, vision_source_radio], outputs=image_output)
        
        with gr.Tab("ℹ️ About"):
            gr.Markdown("""
            ## 🎯 Hybrid RAG + Vision Bot (With Local & API Options)
            
            This is a **versatile Telegram bot** that combines RAG and Vision capabilities with dual model support:
            
            ### 1️⃣ RAG (Text Q&A) - Dual Model Support
            - **OpenRouter API Mode**: Uses GPT-3.5-turbo for high-quality answers
            - **Local Model Mode**: Uses TinyLlama (lightweight, works offline)
            - Stores knowledge base in `data/docs/`
            - Retrieves relevant chunks using semantic search (sentence-transformers)
            - Provides source citations
            
            **Telegram command**: `/ask <question>`
            
            ### 2️⃣ Vision (Image Captioning) - Dual Model Support
            - **OpenRouter API Mode**: Uses Mistral-Large for detailed image descriptions
            - **Local Model Mode**: Uses ViT-GPT2 image captioning (lightweight, offline)
            - Generates detailed image descriptions
            - Extracts 3 key tags from the image
            
            **Telegram command**: `/image` (then upload an image)
            
            ### Technical Stack
            - **Bot Framework**: python-telegram-bot 20.7
            - **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
            - **Vector DB**: SQLite with cosine similarity
            
            **Text Models:**
            - API: OpenRouter (gpt-3.5-turbo)
            - Local: TinyLlama (lightweight, better quality)
            
            **Vision Models:**
            - API: Mistral-Large (OpenRouter)
            - Local: ViT-GPT2 image captioning
            
            - **Web UI**: Gradio (this interface for testing)
            
            ### Model Selection
            - **API Mode**: Better quality, requires internet, uses OpenRouter API key
            - **Local Mode**: Works offline, smaller responses, lower latency, no API costs
            
            ### Available Telegram Commands

            - `/ask <query>` — Query the knowledge base
            - `/image` — Enter image description mode (then upload image)
            - `/help` — Show available commands
            """)
    
    return demo

if __name__ == "__main__":
    demo = build_gradio_ui()
    print("\n" + "="*80)
    print("🚀 Starting Gradio Debug Interface for Hybrid Bot")
    print("="*80)
    print("📊 Features: RAG Q&A + Image Captioning")
    print("🔧 Debug Mode: ENABLED (showing logs)")
    print("\n🌐 Open in browser: http://localhost:7860")
    print("="*80 + "\n")
    demo.launch(share=False, debug=True)
