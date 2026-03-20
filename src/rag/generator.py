"""Advanced Generator with Tree-of-Thought Reasoning for Intelligent RAG
Implements structured reasoning for better answer generation and intent understanding
"""
import requests
from src.config import OPENROUTER_KEY
from typing import List, Dict

# --- Configuration ---
# Ollama Local Model - Fast, Free, Local LLM
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:1b"

# Fallback API Models
API_MODEL = "openai/gpt-3.5-turbo"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Default mode - Use Ollama local model (fast and free), fallback to API
USE_OLLAMA = True  # Set to False to use OpenRouter API

def set_model_source(use_ollama: bool = True):
    """Switch between Ollama and API models"""
    global USE_OLLAMA
    USE_OLLAMA = use_ollama


class TreeOfThoughtReasoner:
    """Implements Tree-of-Thought reasoning for structured answer generation"""
    
    @staticmethod
    def analyze_chunks(query: str, chunks: List[Dict]) -> Dict:
        """Analyze chunks to understand relationships and extract key insights"""
        analysis = {
            'chunk_count': len(chunks),
            'sources': list(set(c['source'] for c in chunks)),
            'combined_text': '\n\n'.join([c['chunk_text'] for c in chunks]),
            'total_length': sum(len(c['chunk_text']) for c in chunks),
            'key_sources': list(set(c['source'] for c in chunks[:2]))
        }
        return analysis
    
    @staticmethod
    def build_reasoning_steps(query: str, chunk_analysis: Dict) -> List[str]:
        """Generate structured reasoning steps"""
        steps = [
            f"1. Understanding the Query: '{query}'",
            f"2. Analyzing {chunk_analysis['chunk_count']} relevant sources: {', '.join(chunk_analysis['sources'])}",
            f"3. Extracting key concepts from primary sources: {', '.join(chunk_analysis['key_sources'])}",
            f"4. Synthesizing information from all sources",
            f"5. Formulating comprehensive answer"
        ]
        return steps
    
    @staticmethod
    def identify_concept_relationships(chunks: List[Dict]) -> Dict:
        """Identify relationships between concepts in chunks"""
        combined = '\n'.join([c['chunk_text'] for c in chunks]).lower()
        
        relationships = {
            'mentioned_together': [],
            'logical_flow': 'sequential' if any(x in combined for x in ['first', 'then', 'next', 'finally']) else 'contextual',
            'comparative': any(x in combined for x in ['unlike', 'different', 'compare', 'vs']),
            'causal': any(x in combined for x in ['because', 'therefore', 'causes', 'leads to'])
        }
        
        return relationships


def build_prompt_with_reasoning(query: str, chunks: List[Dict]) -> str:
    """Build prompt with Tree-of-Thought structure"""
    chunk_analysis = TreeOfThoughtReasoner.analyze_chunks(query, chunks)
    reasoning_steps = TreeOfThoughtReasoner.build_reasoning_steps(query, chunk_analysis)
    concept_relationships = TreeOfThoughtReasoner.identify_concept_relationships(chunks)
    
    context = "\n\n".join([f"[Source: {c['source']}]\n{c['chunk_text']}" for c in chunks])
    
    # Build structured prompt
    prompt = f"""You are an intelligent RAG assistant. Use the following structured approach:

{chr(10).join(reasoning_steps)}

Context from {len(chunks)} sources:
{context}

Relationships in sources:
- Flow Type: {concept_relationships['logical_flow']}
- Contains Comparisons: {concept_relationships['comparative']}
- Contains Causal Relationships: {concept_relationships['causal']}

Question: {query}

Provide a comprehensive answer that:
1. Directly addresses the question
2. Synthesizes information from all sources
3. Maintains context and relationships between concepts
4. Cites which source each key point comes from
5. Explains the logical flow and connections

Answer:"""
    
    return prompt


def build_prompt(query: str, chunks: list[dict]) -> str:
    """Build standard prompt (backward compatible)"""
    context = "\n\n".join([f"[{c['source']}]: {c['chunk_text']}" for c in chunks])
    return f"""You are a helpful assistant. Answer the user's question using ONLY the provided context. If the context doesn't contain the answer, say you don't have enough information.

Context:
{context}

Question: {query}

Answer:"""

def generate(query: str, chunks: list[dict], use_ollama: bool = None, use_tree_of_thought: bool = True) -> str:
    """
    Generate answer using Ollama local model or OpenRouter API.
    
    Args:
        query: User's question
        chunks: Retrieved context chunks
        use_ollama: Override global setting (None = use global USE_OLLAMA)
        use_tree_of_thought: Enable structured reasoning (default True)
    """
    if not chunks:
        return "I could not find any relevant information in the knowledge base."

    mode = use_ollama if use_ollama is not None else USE_OLLAMA
    
    if mode:
        return _generate_ollama(query, chunks)
    else:
        return _generate_api(query, chunks, use_tree_of_thought)

def _generate_ollama(query: str, chunks: list[dict]) -> str:
    """Generate answer using Ollama local model (llama3.2:1b)
    
    Fast, free, runs locally without API keys
    """
    try:
        # Build simple, effective prompt
        context = "\n\n".join([
            f"[Source: {c['source']}]\n{c['chunk_text']}" for c in chunks
        ])
        
        prompt = f"""You are a helpful assistant. Answer the question using ONLY the provided context.
If the context doesn't contain the answer, say you don't have enough information.

Context:
{context}

Question: {query}

Answer:"""
        
        # Call Ollama API
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 300,  # Max tokens to generate
                "top_p": 0.9
            }
        }, timeout=120)
        
        response.raise_for_status()
        answer = response.json()["response"].strip()
        
        return answer if answer else _fallback_answer(query, chunks)
        
    except requests.exceptions.ConnectionError:
        print("❌ Ollama is not running on http://localhost:11434")
        print("   Start Ollama with: ollama serve")
        return _fallback_answer(query, chunks)
    except Exception as e:
        print(f"⚠️ Ollama Error: {str(e)}")
        return _fallback_answer(query, chunks)

def _generate_api(query: str, chunks: list[dict], use_tree_of_thought: bool = True) -> str:
    """Generate answer using OpenRouter API with optional Tree-of-Thought"""
    # Use Tree-of-Thought prompt if enabled
    if use_tree_of_thought:
        prompt = build_prompt_with_reasoning(query, chunks)
    else:
        prompt = build_prompt(query, chunks)
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "RAG Bot"
        }
        
        payload = {
            "model": API_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 400
        }
        
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            answer = result["choices"][0]["message"]["content"].strip()
            return answer
        else:
            return _fallback_answer(query, chunks)
            
    except Exception as e:
        print(f"⚠️ OpenRouter API Error: {str(e)}")
        return _fallback_answer(query, chunks)

def _fallback_answer(query: str, chunks: list[dict]) -> str:
    """Fallback answer generation when API is unavailable"""
    # Extract key information from chunks
    answer = f"Based on the available information:\n\n"
    
    # Combine chunks into a coherent answer
    for i, chunk in enumerate(chunks, 1):
        # Clean up the chunk text
        chunk_text = chunk['chunk_text'].strip()
        if len(chunk_text) > 150:
            chunk_text = chunk_text[:150] + "..."
        answer += f"{i}. {chunk_text}\n\n"
    
    return answer.strip()
