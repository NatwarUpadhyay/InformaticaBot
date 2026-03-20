import uvicorn
from fastapi import FastAPI, Request
import gradio as gr
import json

from src.bot.handlers import ask_handler
from ui.gradio_app import build_gradio_ui

app = FastAPI()

@app.get("/")
def index():
    return {"message": "RAG Bot Server is running", "ui": "http://localhost:8000/ui"}

@app.post("/telegram")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates"""
    try:
        data = await request.json()
        # For now, just acknowledge the webhook
        # In production, would parse and route to telegram handlers
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/health")
def health():
    return {"status": "healthy"}

# Mount Gradio UI
try:
    gradio_ui = build_gradio_ui()
    app = gr.mount_gradio_app(app, gradio_ui, path="/ui")
    print("✓ Gradio UI mounted at /ui")
except Exception as e:
    print(f"⚠ Warning: Could not mount Gradio UI: {e}")

if __name__ == "__main__":
    print("Starting RAG Bot Server...")
    print("- Main server: http://localhost:8000")
    print("- Gradio UI: http://localhost:8000/ui")
    print("- Health check: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
