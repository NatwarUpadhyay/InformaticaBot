import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
HF_TOKEN = os.getenv("HF_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
DB_PATH = os.getenv("DB_PATH", "vector_store.sqlite")
