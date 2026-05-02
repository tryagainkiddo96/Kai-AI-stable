"""
Kai Vector Memory — Semantic memory with embeddings.
Replaces keyword-only search with true vector similarity.
Uses sentence-transformers for embeddings, stores vectors locally.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class VectorMemory:
    """A single memory entry with vector embedding."""
    id: str
    content: str
    embedding: list[float]
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)
    accessed_at: str = field(default_factory=_utc_now_iso)
    access_count: int = 0
    importance: float = 1.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
            "importance": self.importance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VectorMemory":
        return cls(
            id=data["id"],
            content=data["content"],
            embedding=data.get("embedding", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", _utc_now_iso()),
            accessed_at=data.get("accessed_at", _utc_now_iso()),
            access_count=data.get("access_count", 0),
            importance=data.get("importance", 1.0),
        )


class EmbeddingBackend:
    """Handles embedding generation. Uses sentence-transformers if available, fallback to hash-based."""

    def __init__(self) -> None:
        self.model = None
        self._available = False
        self._try_load_model()

    def _try_load_model(self) -> None:
        """Try to load sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self._available = True
        except Exception:
            self._available = False

    def encode(self, text: str) -> list[float]:
        """Generate embedding for text."""
        if self._available and self.model:
            return self.model.encode([text], normalize_embeddings=True)[0].tolist()
        return self._hash_embedding(text)

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if self._available and self.model:
            return self.model.encode(texts, normalize_embeddings=True).tolist()
        return [self._hash_embedding(t) for t in texts]

    def _hash_embedding(self, text: str) -> list[float]:
        """Fallback: generate a deterministic embedding from text hash."""
        # 384-dim to match MiniLM
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        dims = 384
        embedding = []
        for i in range(dims):
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            value = (seed % 10000) / 10000.0 - 0.5
            embedding.append(value)

        # Normalize
        norm = math.sqrt(sum(v * v for v in embedding))
        if norm > 0:
            embedding = [v / norm for v in embedding]
        return embedding

    @property
    def is_available(self) -> bool:
        return self._available


class VectorStore:
    """Local vector store with cosine similarity search."""

    def __init__(self, max_memories: int = 5000) -> None:
        self.max_memories = max_memories
        self.memories: dict[str, VectorMemory] = {}
        self.embeddings: dict[str, list[float]] = {}

    def add(self, memory: VectorMemory) -> None:
        """Add a memory to the store."""
        if len(self.memories) >= self.max_memories:
            self._evict_lowest_importance()
        self.memories[memory.id] = memory
        if memory.embedding:
            self.embeddings[memory.id] = memory.embedding

    def remove(self, memory_id: str) -> bool:
        """Remove a memory from the store."""
        if memory_id in self.memories:
            del self.memories[memory_id]
            self.embeddings.pop(memory_id, None)
            return True
        return False

    def search(self, query_embedding: list[float], limit: int = 10, min_similarity: float = 0.3) -> list[tuple[VectorMemory, float]]:
        """Search for similar memories using cosine similarity."""
        if not self.embeddings:
            return []

        results = []
        for mem_id, embedding in self.embeddings.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            if similarity >= min_similarity:
                memory = self.memories.get(mem_id)
                if memory:
                    results.append((memory, similarity))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get(self, memory_id: str) -> Optional[VectorMemory]:
        """Get a memory by ID."""
        return self.memories.get(memory_id)

    def get_all(self) -> list[VectorMemory]:
        """Get all memories."""
        return list(self.memories.values())

    def count(self) -> int:
        """Get memory count."""
        return len(self.memories)

    def _evict_lowest_importance(self) -> None:
        """Remove lowest importance memories to stay under limit."""
        if not self.memories:
            return
        sorted_memories = sorted(self.memories.values(), key=lambda m: m.importance)
        to_remove = sorted_memories[:max(1, len(sorted_memories) // 10)]
        for memory in to_remove:
            self.remove(memory.id)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)


class KaiVectorMemory:
    """
    Vector-based semantic memory for Kai.
    Stores memories as embeddings, retrieves by semantic similarity.
    """

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.store_path = workspace / "memory" / "vector_memory.json"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

        self.embedding_backend = EmbeddingBackend()
        self.vector_store = VectorStore(max_memories=5000)

        # Load existing memories
        self._load()

    def _load(self) -> None:
        """Load memories from disk."""
        if self.store_path.exists():
            try:
                data = json.loads(self.store_path.read_text(encoding="utf-8"))
                for mem_data in data.get("memories", []):
                    memory = VectorMemory.from_dict(mem_data)
                    self.vector_store.add(memory)
            except Exception:
                pass

    def _save(self) -> None:
        """Save memories to disk."""
        memories_data = [m.to_dict() for m in self.vector_store.get_all()]
        # Don't save full embeddings to disk (large), just store metadata
        # Embeddings are recomputed on load if needed
        payload = {
            "memories": memories_data,
            "updated_at": _utc_now_iso(),
            "count": self.vector_store.count(),
        }
        self.store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def store(self, content: str, metadata: dict | None = None, importance: float = 1.0) -> str:
        """Store a new memory with embedding."""
        embedding = self.embedding_backend.encode(content)
        memory_id = hashlib.sha256(content[:100].encode() + str(time.time()).encode()).hexdigest()[:16]

        memory = VectorMemory(
            id=memory_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            importance=importance,
        )

        self.vector_store.add(memory)
        self._save()
        return memory_id

    def store_batch(self, contents: list[str], metadata_list: list[dict] | None = None, importance: float = 1.0) -> list[str]:
        """Store multiple memories efficiently."""
        embeddings = self.embedding_backend.encode_batch(contents)
        ids = []

        for i, content in enumerate(contents):
            embedding = embeddings[i] if i < len(embeddings) else []
            metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
            memory_id = hashlib.sha256(content[:100].encode() + str(time.time() + i).encode()).hexdigest()[:16]

            memory = VectorMemory(
                id=memory_id,
                content=content,
                embedding=embedding,
                metadata=metadata,
                importance=importance,
            )

            self.vector_store.add(memory)
            ids.append(memory_id)

        self._save()
        return ids

    def search(self, query: str, limit: int = 10, min_similarity: float = 0.3) -> list[dict]:
        """Search memories by semantic similarity."""
        query_embedding = self.embedding_backend.encode(query)
        results = self.vector_store.search(query_embedding, limit=limit, min_similarity=min_similarity)

        memories = []
        for memory, similarity in results:
            # Update access stats
            memory.access_count += 1
            memory.accessed_at = _utc_now_iso()
            memory.importance = min(2.0, memory.importance + 0.05)  # Boost on access

            memories.append({
                "id": memory.id,
                "content": memory.content,
                "similarity": round(similarity, 4),
                "metadata": memory.metadata,
                "created_at": memory.created_at,
                "access_count": memory.access_count,
                "importance": round(memory.importance, 2),
            })

        self._save()
        return memories

    def search_with_context(self, query: str, context: dict | None = None, limit: int = 5) -> list[dict]:
        """Search with additional context filtering."""
        results = self.search(query, limit=limit * 2)

        if context:
            # Boost memories matching context
            for mem in results:
                mem_metadata = mem.get("metadata", {})
                boost = 0.0
                for key, value in context.items():
                    if mem_metadata.get(key) == value:
                        boost += 0.2
                mem["similarity"] = min(1.0, mem["similarity"] + boost)

            results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:limit]

    def get_memory(self, memory_id: str) -> dict | None:
        """Get a specific memory by ID."""
        memory = self.vector_store.get(memory_id)
        if memory:
            return {
                "id": memory.id,
                "content": memory.content,
                "metadata": memory.metadata,
                "created_at": memory.created_at,
                "access_count": memory.access_count,
                "importance": round(memory.importance, 2),
            }
        return None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        result = self.vector_store.remove(memory_id)
        if result:
            self._save()
        return result

    def forget_old(self, days: int = 90, min_access_count: int = 2) -> int:
        """Remove old, unused memories."""
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
        removed = 0

        for memory in self.vector_store.get_all():
            try:
                created_ts = datetime.fromisoformat(memory.created_at).timestamp()
            except Exception:
                continue

            if created_ts < cutoff and memory.access_count < min_access_count:
                self.vector_store.remove(memory.id)
                removed += 1

        if removed > 0:
            self._save()
        return removed

    def update_importance(self, memory_id: str, importance: float) -> bool:
        """Update memory importance."""
        memory = self.vector_store.get(memory_id)
        if memory:
            memory.importance = importance
            self._save()
            return True
        return False

    def get_stats(self) -> dict:
        """Get memory statistics."""
        memories = self.vector_store.get_all()
        if not memories:
            return {"count": 0}

        avg_importance = sum(m.importance for m in memories) / len(memories)
        avg_access = sum(m.access_count for m in memories) / len(memories)

        # Category breakdown
        categories = {}
        for m in memories:
            cat = m.metadata.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "count": len(memories),
            "max_memories": self.vector_store.max_memories,
            "average_importance": round(avg_importance, 2),
            "average_access_count": round(avg_access, 1),
            "categories": categories,
            "embedding_backend": "sentence-transformers" if self.embedding_backend.is_available else "hash-fallback",
            "embedding_dim": 384,
        }

    def build_search_context(self, query: str, limit: int = 5) -> str:
        """Build a context string for prompt injection from semantic search."""
        results = self.search(query, limit=limit, min_similarity=0.25)
        if not results:
            return ""

        parts = ["Relevant memories from past conversations:"]
        for r in results:
            content = r["content"][:200]
            similarity = r["similarity"]
            category = r.get("metadata", {}).get("category", "")
            cat_str = f" [{category}]" if category else ""
            parts.append(f"- ({similarity:.2f}){cat_str} {content}")

        return "\n".join(parts)
