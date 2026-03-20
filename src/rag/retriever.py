"""Advanced Retriever with Intent Recognition & Semantic Chunking
Implements multi-level retrieval with query expansion and intent detection for intelligent RAG
"""
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
from src.config import DB_PATH
from typing import List, Dict

EMBED_MODEL = "all-MiniLM-L6-v2"
_model = None  # lazy load

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model

def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


class QueryIntentAnalyzer:
    """Analyzes user intent to improve retrieval"""
    
    @staticmethod
    def detect_intent(query: str) -> Dict[str, any]:
        """
        Detect query intent and extract key concepts
        Returns: {
            'intent': 'definition|comparison|how-to|explanation|factual',
            'key_terms': [...],
            'expansion_queries': [...]
        }
        """
        query_lower = query.lower()
        
        # Intent detection
        if any(x in query_lower for x in ['what is', 'define', 'meaning', 'explain']):
            intent = 'definition'
        elif any(x in query_lower for x in ['compare', 'difference', 'vs', 'versus']):
            intent = 'comparison'
        elif any(x in query_lower for x in ['how to', 'how do', 'steps', 'process']):
            intent = 'how-to'
        elif any(x in query_lower for x in ['why', 'reason', 'cause']):
            intent = 'explanation'
        else:
            intent = 'factual'
        
        # Extract key terms
        key_terms = [w for w in query.split() if len(w) > 3 and w.lower() not in 
                     ['what', 'this', 'that', 'from', 'with', 'does', 'have']]
        
        # Generate expansion queries for better retrieval
        expansion_queries = []
        if intent == 'definition':
            expansion_queries = [
                f"{key_terms[0]} overview" if key_terms else "",
                f"what is {query}",
            ]
        elif intent == 'comparison' and len(key_terms) >= 2:
            expansion_queries = [
                f"{key_terms[0]} {key_terms[1]} differences",
                f"compare {key_terms[0]} {key_terms[1]}"
            ]
        elif intent == 'how-to':
            expansion_queries = [
                f"steps for {' '.join(key_terms)}",
                f"guide to {' '.join(key_terms)}"
            ]
        
        expansion_queries = [q for q in expansion_queries if q]
        
        return {
            'intent': intent,
            'key_terms': key_terms,
            'expansion_queries': expansion_queries
        }


def _similarity_search(query: str, model, top_k: int = 5) -> List[Dict]:
    """Basic similarity search - returns top-k chunks"""
    query_embedding = model.encode(query).astype(np.float32)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        results = conn.execute("""
            SELECT c.id, c.chunk_text, c.source, v.embedding
            FROM vec_chunks v
            JOIN chunks c ON c.id = v.chunk_id
        """).fetchall()
        
        similarities = []
        for row in results:
            embedding = np.frombuffer(row["embedding"], dtype=np.float32)
            similarity = cosine_similarity(query_embedding, embedding)
            similarities.append({
                "chunk_text": row["chunk_text"],
                "source": row["source"],
                "similarity": similarity,
                "id": row["id"]
            })
        
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]
    finally:
        conn.close()


def _deduplicate_and_rank(primary: List[Dict], expansion: List[Dict], top_k: int) -> List[Dict]:
    """Merge primary and expansion results, remove duplicates"""
    seen = {}
    
    # Add primary results with priority
    for chunk in primary:
        chunk_id = chunk['id']
        if chunk_id not in seen:
            chunk['rank_score'] = chunk['similarity']
            chunk['from_expansion'] = False
            seen[chunk_id] = chunk
    
    # Add expansion results, boosting if already seen
    for chunk in expansion:
        chunk_id = chunk['id']
        if chunk_id in seen:
            seen[chunk_id]['rank_score'] = (seen[chunk_id]['rank_score'] + chunk['similarity']) / 2
            seen[chunk_id]['boost'] = True
        else:
            chunk['rank_score'] = chunk['similarity'] * 0.8
            chunk['from_expansion'] = True
            seen[chunk_id] = chunk
    
    results = list(seen.values())
    results.sort(key=lambda x: x['rank_score'], reverse=True)
    return results[:top_k]


def _score_by_intent(chunks: List[Dict], intent_info: Dict) -> List[Dict]:
    """Rerank chunks based on intent-specific scoring"""
    intent = intent_info['intent']
    key_terms = intent_info['key_terms']
    
    for chunk in chunks:
        text = chunk['chunk_text'].lower()
        base_score = chunk['rank_score']
        boost = 1.0
        
        if intent == 'definition':
            if any(x in text[:100] for x in ['is a', 'refers to', 'means', 'defined as']):
                boost *= 1.3
        elif intent == 'comparison':
            if any(x in text for x in ['difference', 'comparison', 'unlike', 'vs', 'while']):
                boost *= 1.3
        elif intent == 'how-to':
            if any(x in text for x in ['step', 'process', 'follow', 'first', 'next', 'then']):
                boost *= 1.3
        elif intent == 'explanation':
            if any(x in text for x in ['because', 'reason', 'result', 'leads to', 'caused by']):
                boost *= 1.3
        
        key_term_count = sum(1 for term in key_terms if term.lower() in text)
        if key_term_count >= 2:
            boost *= 1.2
        
        chunk['relevance_score'] = base_score * boost
    
    chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
    return chunks


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """
    Main retrieve function - Advanced intent-aware retrieval for intelligent RAG
    Returns: [{"chunk_text": str, "source": str, "distance": float, "id": int}]
    """
    model = get_model()
    
    # Analyze intent
    intent_info = QueryIntentAnalyzer.detect_intent(query)
    
    # Primary search with original query
    primary_results = _similarity_search(query, model, top_k=top_k)
    
    # Expansion search with related queries
    expansion_results = []
    for exp_query in intent_info['expansion_queries'][:2]:
        exp_results = _similarity_search(exp_query, model, top_k=2)
        expansion_results.extend(exp_results)
    
    # Deduplicate and rank
    all_chunks = _deduplicate_and_rank(primary_results, expansion_results, top_k)
    
    # Rerank by intent
    ranked_chunks = _score_by_intent(all_chunks, intent_info)
    
    # Return only essential fields for generator (backward compatible)
    return [
        {
            'chunk_text': c['chunk_text'],
            'source': c['source'],
            'distance': c.get('relevance_score', c.get('rank_score', c['similarity'])),
            'id': c['id']
        }
        for c in ranked_chunks[:top_k]
    ]


def retrieve_detailed(query: str, top_k: int = 3) -> Dict:
    """Advanced retrieval with full diagnostic info for analysis"""
    model = get_model()
    intent_info = QueryIntentAnalyzer.detect_intent(query)
    
    primary_results = _similarity_search(query, model, top_k=top_k)
    expansion_results = []
    for exp_query in intent_info['expansion_queries'][:2]:
        exp_results = _similarity_search(exp_query, model, top_k=2)
        expansion_results.extend(exp_results)
    
    all_chunks = _deduplicate_and_rank(primary_results, expansion_results, top_k)
    ranked_chunks = _score_by_intent(all_chunks, intent_info)
    
    return {
        'intent': intent_info['intent'],
        'key_terms': intent_info['key_terms'],
        'expansion_queries': intent_info['expansion_queries'],
        'primary_results': primary_results[:top_k],
        'expansion_results': expansion_results[:top_k],
        'ranked_chunks': ranked_chunks[:top_k],
        'total_relevant_chunks': len(all_chunks)
    }
