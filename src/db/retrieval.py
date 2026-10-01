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

# Cache for table embeddings: {conn_key: {table_name: (desc_hash, vector)}}
_table_embeddings_cache: dict[str, dict[str, tuple[str, list[float]]]] = {}


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


def invalidate_table_embeddings(connection_id: str | None = None) -> None:
    """Clear cached table embeddings for a specific connection or all connections."""
    global _table_embeddings_cache
    conn_key = connection_id or "default"
    if conn_key in _table_embeddings_cache:
        del _table_embeddings_cache[conn_key]


def precompute_table_embeddings(connection_id: str | None = None) -> int:
    """Precompute and cache table embeddings for the given connection.

    Returns the number of tables embedded.
    """
    all_tables = get_connection_schema(connection_id)
    if not all_tables:
        return 0

    conn_key = connection_id or "default"
    if conn_key not in _table_embeddings_cache:
        _table_embeddings_cache[conn_key] = {}

    import hashlib
    embeddings = _get_embeddings()
    tables_to_embed = []
    texts_to_embed = []
    hashes = []

    for t_name, t_meta in all_tables.items():
        desc = describe_table(t_meta)
        desc_hash = hashlib.md5(desc.encode("utf-8")).hexdigest()
        cached = _table_embeddings_cache[conn_key].get(t_name)
        if not cached or cached[0] != desc_hash:
            tables_to_embed.append(t_name)
            texts_to_embed.append(desc)
            hashes.append(desc_hash)

    if texts_to_embed:
        vectors = embeddings.embed_documents(texts_to_embed)
        for t_name, h, vec in zip(tables_to_embed, hashes, vectors):
            _table_embeddings_cache[conn_key][t_name] = (h, vec)

    return len(all_tables)


def retrieve_candidate_tables(question: str, top_k: int = 25, connection_id: str | None = None) -> dict:
    """Narrow the active database schema to the most relevant tables for the question.

    Uses pre-cached table embeddings with differential embedding for any modified/new
    tables, computing cosine similarity against the question embedding.
    """
    all_tables = get_connection_schema(connection_id)

    if not all_tables:
        return {}

    table_names = list(all_tables.keys())
    conn_key = connection_id or "default"

    try:
        import hashlib
        embeddings = _get_embeddings()
        question_emb = embeddings.embed_query(question)

        # Check and populate table cache incrementally
        if conn_key not in _table_embeddings_cache:
            _table_embeddings_cache[conn_key] = {}

        missing_tables = []
        missing_texts = []
        missing_hashes = []

        for t in table_names:
            desc = describe_table(all_tables[t])
            desc_hash = hashlib.md5(desc.encode("utf-8")).hexdigest()
            cached = _table_embeddings_cache[conn_key].get(t)
            if not cached or cached[0] != desc_hash:
                missing_tables.append(t)
                missing_texts.append(desc)
                missing_hashes.append(desc_hash)

        if missing_texts:
            new_embs = embeddings.embed_documents(missing_texts)
            for t, h, vec in zip(missing_tables, missing_hashes, new_embs):
                _table_embeddings_cache[conn_key][t] = (h, vec)

        # Score all tables using cached embeddings
        scores = []
        for t in table_names:
            t_vec = _table_embeddings_cache[conn_key][t][1]
            scores.append(_cosine_similarity(question_emb, t_vec))

        ranked = sorted(zip(table_names, scores), key=lambda x: -x[1])
        top_tables = [name for name, _ in ranked[:top_k]]
        return {t: all_tables[t] for t in top_tables}

    except Exception as e:
        # Fallback to returning candidate tables directly if Ollama/embedding is unreachable
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
