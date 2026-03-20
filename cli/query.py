"""Minimal CLI to query the vector store (Phase 1).
Example: python cli/query.py "what is the refund policy"
"""
import os
import sys
import json
from pathlib import Path

VECTOR_JSON = Path(os.environ.get("VECTOR_DB_PATH", "data/vector_store.json"))


def load_index():
    if not VECTOR_JSON.exists():
        print("Vector store not found. Run scripts/ingest.py first.")
        sys.exit(1)
    with open(VECTOR_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


if __name__ == '__main__':
    q = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else input("Query: ")
    idx = load_index()
    print("Loaded index with", len(idx.get('ids', [])), "items")
    print("(This is a placeholder CLI; next step is similarity search + LLM call)")
