import json
import time
import math
import numpy as np
from pathlib import Path


class VectorMemoryStore:
    def __init__(self, path="memory_store.jsonl"):
        self.path = Path(path)
        self.data = []
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.data.append(json.loads(line))

    def add(self, text, embedding, importance=0.5, source="ai"):
        now = time.time()
        item = {
            "text": text,
            "embedding": embedding.tolist(),
            "importance": float(max(0.0, min(1.0, importance))),
            "source": source,
            "created_at": now,
            "last_accessed_at": now,
            "access_count": 0,
        }
        self.data.append(item)
        self._append(item)

    def search(self, query_embedding, top_k=3):
        now = time.time()
        scored = []
        for item in self.data:
            vec = np.array(item["embedding"], dtype=np.float32)
            similarity = float(np.dot(vec, query_embedding))
            importance = float(item.get("importance", 0.5))
            recency = self._recency_score(item.get("last_accessed_at", item.get("created_at", now)), now)
            frequency = self._frequency_score(item.get("access_count", 0))
            score = similarity * 0.70 + importance * 0.18 + recency * 0.08 + frequency * 0.04
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
