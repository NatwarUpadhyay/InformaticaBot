# 🏗️ System Architecture & Design

## Overview

**InfoMatica Bot** is a hybrid AI assistant combining:
1. **RAG (Retrieval-Augmented Generation)** - Intelligent Q&A from knowledge base
2. **Vision** - Image captioning and tagging

Built with modern Python frameworks, local ML models, and graceful API fallbacks.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      USER INTERFACES                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  Telegram Bot    │  │  Gradio Debug    │  │   CLI Tool     │  │
│  │  (@InfoMatica)   │  │   UI (Port 7860) │  │  (Command line)│  │
│  └──────────────────┘  └──────────────────┘  └────────────────┘  │
│
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      CORE ROUTING LAYER                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Telegram Bot Handlers  /  Gradio Routes  /  CLI Dispatcher       │
│  ↓                      ↓                   ↓                       │
│  ask_command()         RAG_chat()        query_cli()               │
│  image_command()       Vision_chat()     (Direct query)            │
│  help_command()        Model toggle                                 │
│  start_command()                                                    │
│  photo_handler()                                                    │
│
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      PROCESSING PIPELINES                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────┐   ┌─────────────────────────┐  │
│  │  RAG PIPELINE               │   │  VISION PIPELINE        │  │
│  ├─────────────────────────────┤   ├─────────────────────────┤  │
│  │                             │   │                         │  │
│  │ 1. Query Input              │   │ 1. Image Buffer         │  │
│  │    ↓                        │   │    ↓                    │  │
│  │ 2. Intent Detection         │   │ 2. Format Conversion    │  │
│  │    (Classify query type)    │   │    (to PNG)             │  │
│  │    ↓                        │   │    ↓                    │  │
│  │ 3. Query Expansion          │   │ 3. API Request          │  │
│  │    (Add synonyms)           │   │    (Mistral Small 3.1)  │  │
│  │    ↓                        │   │    ↓                    │  │
│  │ 4. Embedding Generation     │   │ 4. Fallback to BLIP     │  │
│  │    (SentenceTransformers)   │   │    (If API fails)       │  │
│  │    ↓                        │   │    ↓                    │  │
│  │ 5. Vector Search            │   │ 5. Parse Response       │  │
│  │    (Cosine Similarity)      │   │    (Extract caption)    │  │
│  │    ↓                        │   │    ↓                    │  │
│  │ 6. Chunk Ranking            │   │ 6. Extract Tags         │  │
│  │    (Relevance score)        │   │    (3 keywords)         │  │
│  │    ↓                        │   │    ↓                    │  │
│  │ 7. Prompt Building          │   │ 7. Format Output        │  │
│  │    (Context + question)     │   │    (Caption + Tags)     │  │
│  │    ↓                        │   │                         │  │
│  │ 8. LLM Generation           │   │                         │  │
│  │    (Ollama primary)         │   │                         │  │
│  │    ↓                        │   │                         │  │
│  │ 9. Fallback to API          │   │                         │  │
│  │    (If Ollama fails)        │   │                         │  │
│  │    ↓                        │   │                         │  │
│  │ 10. Response + Sources      │   │                         │  │
│  │     (Answer + citations)    │   │                         │  │
│  │                             │   │                         │  │
│  └─────────────────────────────┘   └─────────────────────────┘  │
│
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA & SERVICES LAYER                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────┐ │
│  │ Knowledge Base     │  │ Embedding Service  │  │ LLM Services │ │
│  ├────────────────────┤  ├────────────────────┤  ├──────────────┤ │
│  │ Documents:         │  │ Model:             │  │ Local:       │ │
│  │ ├─ FAQ.md          │  │ all-MiniLM-L6-v2   │  │ Ollama       │ │
│  │ ├─ FEATURES.md     │  │ (80MB, 384-dim)    │  │ llama3.2:1b  │ │
│  │ ├─ PRICING.md      │  │                    │  │              │ │
│  │ ├─ NIPS Paper.pdf  │  │ Storage:           │  │ Fallback:    │ │
│  │ └─ (145 chunks)    │  │ SQLite (vec0)      │  │ OpenRouter   │ │
│  │                    │  │                    │  │ GPT-3.5      │ │
│  │ Size: ~5MB         │  │ Index: 145 chunks  │  │              │ │
│  └────────────────────┘  └────────────────────┘  └──────────────┘ │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Vision Services                                            │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │ Primary (API):   Mistral Small 3.1 via OpenRouter         │   │
│  │ Fallback (Local): Salesforce BLIP (1.6GB)                 │   │
│  │ Image Processing: PIL (Python Imaging Library)            │   │
│  └────────────────────────────────────────────────────────────┘   │
│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Telegram Bot Layer (`telegram_bot.py`)

**Purpose**: Entry point, connection to Telegram, message routing

**Architecture**:
```python
telegram_bot.py
├── TelegramClient
│   ├── Initialize with token
│   ├── Register handlers
│   └── Start polling
│
├── Handlers (registered with dispatcher)
│   ├── /ask → ask_command()
│   ├── /image → image_command()
│   ├── /help → help_command()
│   ├── /start → start_command()
│   └── Photo → photo_handler()
│
└── Message Loop
    └── Update dispatcher → Route to handler
```

**Key Features**:
- Polling mode (no webhooks)
- Async/await patterns
- Error handling with try-catch
- User context tracking (user_states)
- Message formatting

**Flow**:
```
User sends message
    ↓
Telegram API receives
    ↓
Bot polling retrieves update
    ↓
Dispatcher routes to handler
    ↓
Handler processes (calls RAG/Vision)
    ↓
Response formatted
    ↓
Sent back via Telegram API
```

---

### 2. RAG System (`src/rag/`)

#### 2.1 Retriever (`src/rag/retriever.py`)

**Purpose**: Semantic search over knowledge base

**Responsibilities**:
1. Intent detection
2. Query expansion
3. Embedding generation
4. Vector search
5. Chunk ranking

**Algorithm Flow**:

```python
def retrieve(query, top_k=3):
    
    # Step 1: Intent Detection
    intent = detect_intent(query)
    # Examples: "product_features", "pricing", "technical"
    
    # Step 2: Query Expansion
    expanded_terms = expand_query(query)
    # Original: "features"
    # Expanded: ["features", "capabilities", "functionality"]
    
    # Step 3: Generate Embedding
    query_embedding = embed_text(query)  # 384-dimensional vector
    
    # Step 4: Vector Search
    candidates = vector_search(query_embedding, top_k=10)
    # Cosine similarity search in SQLite
    
    # Step 5: Ranking & Deduplication
    ranked_chunks = rank_and_dedupe(candidates)
    
    # Step 6: Return Top-K
    return ranked_chunks[:top_k]
```

**Data Structures**:
```
Input:  query (str)
Output: [
  {
    "text": "Feature 1: High performance...",
    "source": "FEATURES.md",
    "score": 0.95,
    "chunk_id": 42
  },
  ...
]
```

**Vector Database Schema**:
```sql
CREATE TABLE embeddings (
    chunk_id INTEGER PRIMARY KEY,
    content TEXT,
    source TEXT,
    embedding BLOB,  -- 384-dimensional vector
    sequence INTEGER  -- Position in document
);

CREATE INDEX idx_source ON embeddings(source);
```

---

#### 2.2 Generator (`src/rag/generator.py`)

**Purpose**: Generate answers using LLM

**Dual-Model Strategy**:

```
Query + Context + System Prompt
        ↓
    ┌─────────────────┐
    │  Use Ollama?    │
    │  (Enabled)      │
    └─────────────────┘
        ↓ YES
    ┌──────────────────────────┐
    │ Call Ollama llama3.2:1b  │
    │ (Local, 2-3s, free)      │
    └──────────────────────────┘
        ↓ SUCCESS
    Return answer
        
        ↓ FAIL (timeout/connection error)
    ┌──────────────────────────┐
    │ Call OpenRouter API      │
    │ (GPT-3.5, 3-5s)          │
    └──────────────────────────┘
        ↓ SUCCESS
    Return answer
        
        ↓ FAIL
    Return error message
```

**Prompt Construction**:
```
System Prompt:
"You are a helpful AI assistant. Answer questions based on the 
provided context. If you can't find the answer, say so."

Context:
"From [source]: [chunk1]\n[chunk2]\n[chunk3]"

User Query:
"What are your features?"

Final Prompt:
System + Context + Query → LLM
```

**Configuration Options**:
```python
generate(
    query="What features?",
    chunks=[...],
    use_ollama=True,      # Primary model
    temperature=0.7,      # Creativity level
    max_tokens=500        # Response length
)
```

---

### 3. Vision System (`src/vision/captioner.py`)

**Purpose**: Image analysis (caption + tags)

**Triple Fallback Strategy**:

```
Image Buffer
    ↓
Try: Mistral Small 3.1 (OpenRouter API)
├─ Success → Extract caption + tags → Return
│
└─ Fail (API error/timeout)
    ↓
    Try: Salesforce BLIP (Local)
    ├─ Success → Extract caption + tags → Return
    │
    └─ Fail (Model error)
        ↓
        Return: Generic error message
```

**Image Processing Pipeline**:

```python
def caption_image(image_bytes):
    
    # Step 1: Validate
    if not validate_image(image_bytes):
        return error
    
    # Step 2: Convert format
    image = convert_to_png(image_bytes)
    
    # Step 3: API Request
    try:
        response = call_mistral_api(image)
        caption = extract_caption(response)
        tags = extract_tags(response)
        return format_output(caption, tags)
    
    # Step 4: Fallback to BLIP
    except APIError:
        blip_result = caption_with_blip(image)
        return format_output(blip_result)
```

**Output Format**:
```python
{
    "caption": "A serene mountain landscape with snow-capped peaks",
    "tags": ["mountain", "nature", "landscape"]
}
```

**API Integration**:

```
OpenRouter Request:
{
    "model": "mistralai/mistral-small-3.1",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Caption this image:"},
            {"type": "image_url", "image_url": {"url": "data:image/..."}},
            {"type": "text", "text": "Return format: CAPTION: ... TAGS: ..."}
        ]
    }]
}
```

---

### 4. Embedding & Vector Storage

**Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2`

**Characteristics**:
- Lightweight: 80MB
- Dimension: 384
- Speed: ~1000+ embeddings/sec
- Accuracy: Good for semantic search
- Offline capable: Yes

**Vector Storage**: SQLite with vec0 extension

**Indexing Process**:

```
Raw Documents
    ↓
Chunking (300 chars, 50 overlap)
    ├─ FAQ.md           → 5 chunks
    ├─ FEATURES.md      → 5 chunks
    ├─ PRICING.md       → 4 chunks
    └─ NIPS Paper.pdf   → 131 chunks (research content)
    ↓
Total: 145 chunks
    ↓
Embedding Generation
    (Vectorize each chunk)
    ↓
SQLite Storage
    (Store vectors + metadata)
    ↓
Index Created
    (Ready for similarity search)
```

**Query-Time Flow**:

```
User Query: "What are the features?"
    ↓
Embed query (384-dim vector)
    ↓
Search SQLite for similar embeddings
    (Cosine similarity)
    ↓
Return top-3 chunks with scores:
    1. FEATURES.md chunk 2 (score: 0.95)
    2. FEATURES.md chunk 1 (score: 0.92)
    3. FAQ.md chunk 3 (score: 0.88)
```

---

## Data Flow Diagrams

### RAG Query Flow

```
┌────────────────────────────┐
│ User Message: /ask ...     │
└────────────────────────────┘
            ↓
┌────────────────────────────┐
│ Extract query text         │
└────────────────────────────┘
            ↓
┌────────────────────────────┐
│ retriever.retrieve()       │
│ ├─ Intent detection        │
│ ├─ Query expansion         │
│ ├─ Embedding generation    │
│ ├─ Vector search           │
│ └─ Chunk ranking           │
└────────────────────────────┘
            ↓
┌────────────────────────────┐
│ generator.generate()       │
│ ├─ Build prompt            │
│ ├─ Call Ollama             │
│ └─ Fallback to API         │
└────────────────────────────┘
            ↓
┌────────────────────────────┐
│ Format response            │
│ ├─ Answer text             │
│ ├─ Source citations        │
│ └─ Relevance info          │
└────────────────────────────┘
            ↓
┌────────────────────────────┐
│ Send via Telegram API      │
└────────────────────────────┘
```

### Vision Query Flow

```
┌────────────────────────────┐
│ User sends photo           │
└────────────────────────────┘
            ↓
┌────────────────────────────┐
│ Receive via Telegram API   │
└────────────────────────────┘
            ↓
┌────────────────────────────┐
│ Download image to buffer   │
└────────────────────────────┘
            ↓
┌────────────────────────────┐
│ captioner.caption_image()  │
│ ├─ Validate image          │
│ ├─ Convert format          │
│ └─ Call Mistral (API)      │
└────────────────────────────┘
            ↓
        Success?
       /        \
      YES       NO
      ↓         ↓
   Return    Fall back to BLIP
             ├─ Load model
             ├─ Process image
             └─ Extract caption
                   ↓
            ┌─────────────────┐
            │ Extract caption │
            │ Extract 3 tags  │
            └─────────────────┘
                   ↓
            ┌─────────────────┐
            │ Format response │
            │ CAPTION: ...    │
            │ TAGS: ...       │
            └─────────────────┘
                   ↓
            Send via Telegram
```

---

## Design Decisions

### 1. Why Local Ollama as Primary LLM?

**Pros**:
- ✅ Free (no API costs)
- ✅ Works offline
- ✅ Fast (2-3s latency)
- ✅ Privacy (data stays local)
- ✅ Easy to switch models

**Cons**:
- ❌ Lower quality than GPT-4
- ❌ Requires local hardware
- ❌ llama3.2:1b is small model

**Trade-off**: Great for speed + cost, acceptable quality for FAQ/product questions

### 2. Why sentence-transformers for Embeddings?

**Alternatives Considered**:
- OpenAI embeddings: Too expensive
- Ollama embeddings: Slower
- sqlite-vec: Requires special setup

**Selected**: sentence-transformers
- ✅ Lightweight (80MB)
- ✅ Fast enough
- ✅ No API costs
- ✅ Works offline
- ✅ Good quality

### 3. Why SQLite for Vector DB?

**Alternatives Considered**:
- Pinecone: Cloud-based, costs
- Weaviate: Complex setup
- Milvus: Overkill for small dataset
- FAISS: Fast but no persistence

**Selected**: SQLite with vec0
- ✅ Simple (one file)
- ✅ No server needed
- ✅ Portable
- ✅ Works offline
- ✅ 145 chunks sufficient

### 4. Why Mistral + BLIP for Vision?

**Alternatives Considered**:
- GPT-4V: Expensive
- LLaVA: Slower
- CLIP: Only embeddings, no captions
- ViLBERT: Complex

**Selected**: Mistral + BLIP
- ✅ Mistral free tier available
- ✅ BLIP local fallback
- ✅ Good quality/speed trade-off
- ✅ Graceful degradation

---

## Performance Characteristics

### Query Performance

| Operation | Time | Bottleneck |
|-----------|------|-----------|
| Embedding generation | <100ms | CPU |
| Vector search | <10ms | SQLite query |
| LLM generation (Ollama) | 2-3s | GPU/CPU |
| LLM generation (API) | 3-5s | Network |
| Image captioning (API) | 2-3s | Network |
| Image captioning (BLIP) | 2-3s | GPU |

**Total E2E Time**:
- RAG query (local): ~2.5s
- RAG query (API fallback): ~3.5s
- Image caption (API): ~2.5s
- Image caption (local): ~2.5s

### Resource Usage

| Component | Memory | Disk | Network |
|-----------|--------|------|---------|
| Ollama (llama3.2:1b) | 1.3GB VRAM | 1.3GB | No |
| sentence-transformers | 200MB RAM | 80MB | No |
| BLIP (on demand) | 1.6GB VRAM | 1.6GB | No |
| Vector DB | 10MB RAM | 5MB | No |
| Bot process | 100MB RAM | — | Yes |

**Scalability**:
- Works on: Laptop, edge devices, cloud
- Scales with: More documents (just re-index)
- Bottleneck: LLM VRAM (local inference)

---

## Error Handling & Fallbacks

### RAG Query Error Handling

```python
try:
    chunks = retriever.retrieve(query)
    if not chunks:
        return "No relevant information found"
    
    answer = generator.generate(query, chunks, use_ollama=True)
    
except OllamaError:
    # Try API fallback
    answer = generator.generate(query, chunks, use_ollama=False)
    
except NoAPIKey:
    # Inform user
    return "Generation unavailable (no API key)"
    
except Exception as e:
    # Generic error
    return f"Error: {str(e)}"
```

### Vision Query Error Handling

```python
try:
    # Attempt Mistral API
    result = mistral_api.caption(image)
    return result
    
except APIError:
    # Fallback to BLIP
    try:
        result = blip_model.caption(image)
        return result
    except Exception:
        return "Cannot process image"
        
except Exception:
    return "Error: Image processing failed"
```

---

## Security Considerations

✅ **Implemented**:
- API keys in `.env` (not hardcoded)
- No sensitive data in logs
- Input validation (image size, type)
- Error messages without secrets
- .gitignore configured

📝 **Recommendations**:
- Use secrets manager in production
- Implement rate limiting
- Monitor API usage/costs
- Validate image content
- Restrict document access if needed

---

## Extensibility

### Adding New Documents

1. Copy document to `data/docs/`
2. Run `python scripts/ingest.py`
3. Restart bot
4. Bot automatically retrieves from new docs

### Switching LLM Models

```python
# In src/rag/generator.py
# Change model name:
OLLAMA_MODEL = "mistral:7b"  # Instead of llama3.2:1b
OLLAMA_MODEL = "neural-chat"  # For coding questions
```

### Adding New Commands

```python
# In telegram_bot.py
@app.message_handler(commands=['mycmd'])
def my_command(message):
    # Your implementation
    pass

# Register in main
app.register_message_handler(my_command)
```

### Custom Intent Classes

```python
# In src/rag/retriever.py
INTENTS = {
    "product_features": ["feature", "capabilities", "what do you offer"],
    "pricing": ["price", "cost", "pricing"],
    "custom": ["your", "custom", "terms"],  # ADD HERE
}
```

---

## Monitoring & Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now all operations will print details
```

### Test Individual Components

```bash
# Test retrieval
python -c "from src.rag.retriever import retrieve; print(retrieve('features'))"

# Test generation
python -c "from src.rag.generator import generate; chunks=[...]; print(generate('q', chunks))"

# Test vision
python -c "from src.vision.captioner import caption_image; print(caption_image(b'...'))"
```

### Gradio Debug Interface

```bash
python ui/gradio_app.py
# Open http://localhost:7860
# Test RAG and Vision with real-time logs
```

---

## Deployment Considerations

### Local Development
- ✅ Recommended for testing
- Run: `python telegram_bot.py`

### Production Server
- Use systemd service (Linux)
- Or Docker container
- Monitor Ollama and bot processes
- Implement graceful restart

### Scaling
- Single bot: 1 process
- Multiple users: Works fine
- High volume: Add load balancer, multiple instances

---

## Conclusion

InfoMatica Bot demonstrates:
- ✅ Clean, modular architecture
- ✅ Intelligent design choices
- ✅ Graceful fallback mechanisms
- ✅ Local-first, online-optional approach
- ✅ Production-ready implementation
- ✅ Easy to understand and extend

**Perfect for**: Portfolio projects, AI demonstrations, production deployments, and learning GenAI systems.
