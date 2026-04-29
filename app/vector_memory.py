import json
import numpy as np
from pathlib import Path

class VectorMemoryStore:
    def __init__(self, path="memory_store.jsonl"):
        self.path = Path(path)
        self.data = []
        if self.path.exists():
            with open(self.path, 'r', encoding='utf-8') as f:
                for line in f:
                    self.data.append(json.loads(line))

    def add(self, text, embedding):
        item = {
            "text": text,
            "embedding": embedding.tolist()
        }
        self.data.append(item)
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def search(self, query_embedding, top_k=3):
        scored = []
        for item in self.data:
            vec = np.array(item["embedding"])
            score = float(np.dot(vec, query_embedding))
            scored.append((score, item["text"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for score, text in scored[:top_k]]
