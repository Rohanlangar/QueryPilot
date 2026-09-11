"""
QueryPilot — Semantic Cache

Caches SQL generation results keyed by normalized question hashes,
scoped per database connection. Reduces DB load and LLM API costs
for semantically similar questions.

v1: Normalized text hashing (lowercase, strip, remove stop words).
v2 (future): Embedding-based similarity search.
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.cache_entry import CacheEntry

logger = logging.getLogger(__name__)

# Common English stop words to strip for normalization
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "and", "but", "or",
    "not", "no", "nor", "so", "yet", "both", "either", "neither",
    "each", "every", "all", "any", "few", "more", "most", "other",
    "some", "such", "than", "too", "very", "just", "also", "now",
    "me", "my", "i", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "their", "this", "that", "these", "those",
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "show", "give", "tell", "get", "find", "list", "display", "please",
}


class SemanticCache:
    """
    Cache layer for natural-language-to-SQL mappings.
    Uses normalized text hashing for efficient lookup.
    """

    def _normalize_question(self, question: str) -> str:
        """
        Normalize a question for cache key generation.
        Strips stop words, lowercases, removes punctuation.
        """
        text = question.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)  # Remove punctuation
        words = text.split()
        meaningful = [w for w in words if w not in STOP_WORDS]
        return " ".join(sorted(meaningful))  # Sort for order-independence

    def _hash_question(self, question: str) -> str:
        """Generate SHA-256 hash of normalized question."""
        normalized = self._normalize_question(question)
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def check_cache(
        self,
        question: str,
        connection_id: str,
        db: AsyncSession,
    ) -> Optional[CacheEntry]:
        """
        Check if a semantically similar question has been cached.

        Returns CacheEntry if found and not expired, None otherwise.
        """
        question_hash = self._hash_question(question)
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(CacheEntry).where(
                CacheEntry.connection_id == connection_id,
                CacheEntry.question_hash == question_hash,
                CacheEntry.expires_at > now,
            )
        )
        entry = result.scalar_one_or_none()

        if entry:
            # Update hit tracking
            entry.hit_count += 1
            entry.last_hit_at = now
            await db.flush()
            logger.info(f"Cache hit for hash {question_hash[:12]}... (hits: {entry.hit_count})")

        return entry

    async def store_cache(
        self,
        question: str,
        connection_id: str,
        sql: str = None,
        result_json: Any = None,
        result_row_count: int = None,
        ttl: int = None,
        sql_generated: str = None,
        confidence_score: float = None,
        db: AsyncSession = None,
    ) -> CacheEntry:
        """Store a query result in the cache."""
        if ttl is None:
            ttl = settings.cache_ttl_seconds

        sql_val = sql or sql_generated or ""
        if isinstance(result_json, (dict, list)):
            import json
            result_json_str = json.dumps(result_json)
        else:
            result_json_str = result_json

        now = datetime.now(timezone.utc)
        question_hash = self._hash_question(question)

        entry = CacheEntry(
            connection_id=connection_id,
            question_hash=question_hash,
            question_text=question,
            sql_generated=sql_val,
            result_json=result_json_str,
            result_row_count=result_row_count,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )
        db.add(entry)
        await db.flush()
        logger.info(f"Cached query: hash={question_hash[:12]}... TTL={ttl}s")
        return entry

    async def invalidate_cache(
        self, connection_id: str, db: AsyncSession
    ) -> int:
        """
        Invalidate all cache entries for a connection.
        Useful when schema changes.
        """
        result = await db.execute(
            delete(CacheEntry).where(CacheEntry.connection_id == connection_id)
        )
        count = result.rowcount
        logger.info(f"Invalidated {count} cache entries for connection {connection_id}")
        return count

    async def cleanup_expired(self, db: AsyncSession) -> int:
        """Remove all expired cache entries."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            delete(CacheEntry).where(CacheEntry.expires_at <= now)
        )
        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} expired cache entries")
        return count


# Singleton instance
semantic_cache = SemanticCache()
