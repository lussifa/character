import json
import time
import math
import hashlib
import numpy as np
from pathlib import Path


class VectorMemoryStore:
    CORE = "core"
    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"

    def __init__(self, path="memory_store.jsonl"):
        self.path = Path(path)
        self.data = []
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        item = json.loads(line)
                        item.setdefault("tier", self.LONG_TERM)
                        item.setdefault("memory_id", self._memory_id(item["text"]))
                        self.data.append(item)

    def add(self, text, embedding, importance=0.5, source="ai", tier=LONG_TERM):
        tier = self._normalize_tier(tier)
        now = time.time()
        item = {
            "memory_id": self._memory_id(text),
            "text": text,
            "embedding": embedding.tolist(),
            "importance": float(max(0.0, min(1.0, importance))),
            "source": source,
            "tier": tier,
            "created_at": now,
            "last_accessed_at": now,
            "access_count": 0,
        }

        conflict = self.find_conflict(embedding, threshold=0.92)
        if conflict:
            self._merge_memory(conflict, item)
            self._rewrite()
            return conflict["memory_id"]

        self.data.append(item)
        self._append(item)
        return item["memory_id"]

    def search(self, query_embedding, top_k=5, include_short_term=True):
        now = time.time()
        scored = []
        for item in self.data:
            if item.get("tier") == self.SHORT_TERM and not include_short_term:
                continue

            vec = np.array(item["embedding"], dtype=np.float32)
            similarity = float(np.dot(vec, query_embedding))
            importance = float(item.get("importance", 0.5))
            recency = self._recency_score(item.get("last_accessed_at", item.get("created_at", now)), now)
            frequency = self._frequency_score(item.get("access_count", 0))
            tier_boost = self._tier_boost(item.get("tier", self.LONG_TERM))

            score = similarity * 0.64 + importance * 0.18 + recency * 0.07 + frequency * 0.04 + tier_boost * 0.07
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = []
        for _, item in scored[:top_k]:
            item["last_accessed_at"] = now
            item["access_count"] = int(item.get("access_count", 0)) + 1
            selected.append(item["text"])

        if selected:
            self._rewrite()
        return selected

    def compact_short_term(self, embedder, max_short_term=20):
        short_terms = [m for m in self.data if m.get("tier") == self.SHORT_TERM]
        if len(short_terms) <= max_short_term:
            return None

        short_terms.sort(key=lambda m: m.get("created_at", 0))
        to_compact = short_terms[:-max_short_term]
        summary = "\n".join(f"- {m['text']}" for m in to_compact)
        compacted_text = "Compacted short-term memories:\n" + summary[:4000]
        compacted_embedding = embedder.embed(compacted_text)

        compacted_id = self.add(
            compacted_text,
            compacted_embedding,
            importance=0.6,
            source="compaction",
            tier=self.LONG_TERM,
        )

        compacted_ids = {m["memory_id"] for m in to_compact}
        self.data = [m for m in self.data if m.get("memory_id") not in compacted_ids]
        self._rewrite()
        return compacted_id

    def find_conflict(self, embedding, threshold=0.92):
        best = None
        best_score = -1.0
        for item in self.data:
            vec = np.array(item["embedding"], dtype=np.float32)
            score = float(np.dot(vec, embedding))
            if score > best_score:
                best = item
                best_score = score
        if best and best_score >= threshold:
            return best
        return None

    def _merge_memory(self, existing, incoming):
        existing["text"] = self._merge_text(existing["text"], incoming["text"])
        existing["embedding"] = incoming["embedding"]
        existing["importance"] = max(float(existing.get("importance", 0.5)), float(incoming.get("importance", 0.5)))
        existing["tier"] = self._stronger_tier(existing.get("tier", self.LONG_TERM), incoming.get("tier", self.LONG_TERM))
        existing["last_accessed_at"] = time.time()
        existing["access_count"] = int(existing.get("access_count", 0)) + 1
        existing["source"] = existing.get("source", "") + "+merge"

    @staticmethod
    def _merge_text(a, b):
        if b in a:
            return a
        if a in b:
            return b
        return f"{a}\nUpdated/related memory: {b}"

    @classmethod
    def _stronger_tier(cls, a, b):
        rank = {cls.SHORT_TERM: 0, cls.LONG_TERM: 1, cls.CORE: 2}
        return a if rank.get(a, 1) >= rank.get(b, 1) else b

    @classmethod
    def _normalize_tier(cls, tier):
        if tier not in {cls.CORE, cls.LONG_TERM, cls.SHORT_TERM}:
            return cls.LONG_TERM
        return tier

    @staticmethod
    def _tier_boost(tier):
        if tier == VectorMemoryStore.CORE:
            return 1.0
        if tier == VectorMemoryStore.LONG_TERM:
            return 0.55
        return 0.2

    @staticmethod
    def _memory_id(text):
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def _append(self, item):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def _rewrite(self):
        with open(self.path, "w", encoding="utf-8") as f:
            for item in self.data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    @staticmethod
    def _recency_score(timestamp, now):
        age_hours = max(0.0, (now - float(timestamp)) / 3600.0)
        half_life_hours = 72.0
        return math.exp(-age_hours / half_life_hours)

    @staticmethod
    def _frequency_score(access_count):
        return min(1.0, math.log1p(max(0, int(access_count))) / math.log(10))
