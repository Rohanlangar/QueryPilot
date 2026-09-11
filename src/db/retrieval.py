# db/retrieval.py
"""Embedding-based table retrieval — pre-filters the full schema down to
a small candidate set BEFORE it reaches an LLM prompt.

Uses nomic-embed-text served via Ollama for embeddings, with cosine
similarity ranking against the user's question.

STUB: Full implementation (Phase 4) will populate the schema metadata cache
from a real database. For now, retrieval logic is fully functional but
depends on the metadata cache being populated externally.
"""

import numpy as np
from langchain_ollama import OllamaEmbeddings

from db.connection_manager import get_connection_schema
from config import EMBEDDING_MODEL, OLLAMA_BASE_URL

# Lazy-initialized embeddings client
_embeddings: OllamaEmbeddings | None = None


def _get_embeddings() -> OllamaEmbeddings:
    """Get or create the Ollama embeddings client (singleton)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_BASE_URL,
        )
    return _embeddings


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr) + 1e-10))


def retrieve_candidate_tables(question: str, top_k: int = 25, connection_id: str | None = None) -> dict:
    """Narrow the active database schema to the most relevant tables for the question.

    Embeds each table description via nomic-embed-text (Ollama), computes
    cosine similarity against the question embedding, and returns the top-k.
    Supports dynamic database selection via connection_id.
    """
    all_tables = get_connection_schema(connection_id)

    if not all_tables:
        return {}

    # Build text descriptions for each table
    table_names = list(all_tables.keys())
    table_texts = [describe_table(all_tables[t]) for t in table_names]

    # Try embedding question + all table descriptions via Ollama with graceful fallback
    try:
        embeddings = _get_embeddings()
        question_emb = embeddings.embed_query(question)
        table_embs = embeddings.embed_documents(table_texts)

        # Rank by cosine similarity
        scores = [_cosine_similarity(question_emb, t_emb) for t_emb in table_embs]
        ranked = sorted(zip(table_names, scores), key=lambda x: -x[1])
        top_tables = [name for name, _ in ranked[:top_k]]
        return {t: all_tables[t] for t in top_tables}
    except Exception as e:
        # Fallback to returning candidate tables directly if Ollama is unreachable
        print(f"[Warning] Embedding retrieval failed ({e}), falling back to full table list.")
        return {t: all_tables[t] for t in table_names[:top_k]}


def describe_table(meta: dict) -> str:
    """Build a rich human-readable text description of a table for embedding and schema prompts."""
    cols_meta = meta.get("columns", {})
    samples = meta.get("sample_values", {})
    
    col_descs = []
    for c_name, c_type in cols_meta.items():
        if c_name in samples and samples[c_name]:
            vals_str = ", ".join(repr(v) for v in samples[c_name])
            col_descs.append(f"{c_name} ({c_type}, values: [{vals_str}])")
        else:
            col_descs.append(f"{c_name} ({c_type})")
            
    cols_str = ", ".join(col_descs)
    
    # Foreign keys
    fk_strs = []
    for fk in meta.get("foreign_keys", []):
        constrained = ", ".join(fk.get("constrained_columns", []))
        ref_table = fk.get("referred_table")
        ref_cols = ", ".join(fk.get("referred_columns", []))
        fk_strs.append(f"FK({constrained} -> {ref_table}.{ref_cols})")
    fks_part = f". Relationships: {', '.join(fk_strs)}" if fk_strs else ""

    comment = meta.get("comment")
    comment_part = f". Comment: {comment}" if comment else ""

    return f"Table {meta.get('name', '')}: columns [{cols_str}]{fks_part}{comment_part}"
