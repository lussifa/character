from pathlib import Path

from .vector_memory import VectorMemoryStore


class ScopedMemoryManager:
    def __init__(self, root="memory"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._stores = {}

    def store_for(self, scope="shared"):
        safe_scope = self._safe_scope(scope)
        if safe_scope not in self._stores:
            self._stores[safe_scope] = VectorMemoryStore(path=str(self.root / f"{safe_scope}.jsonl"))
        return self._stores[safe_scope]

    def character_store(self, character_id):
        return self.store_for(f"character_{character_id}")

    def shared_store(self):
        return self.store_for("shared")

    def world_store(self):
        return self.store_for("world")

    def add_character_memory(self, character_id, text, embedding, importance=0.5, source="ai", tier="long_term"):
        return self.character_store(character_id).add(text, embedding, importance=importance, source=source, tier=tier)

    def add_shared_memory(self, text, embedding, importance=0.5, source="ai", tier="long_term"):
        return self.shared_store().add(text, embedding, importance=importance, source=source, tier=tier)

    def add_world_memory(self, text, embedding, importance=0.5, source="ai", tier="long_term"):
        return self.world_store().add(text, embedding, importance=importance, source=source, tier=tier)

    def search_for_character(self, character_id, query_embedding, top_k_character=4, top_k_shared=2, top_k_world=2):
        results = []
        for text in self.character_store(character_id).search(query_embedding, top_k=top_k_character):
            results.append({"scope": f"character:{character_id}", "text": text})
        for text in self.shared_store().search(query_embedding, top_k=top_k_shared):
            results.append({"scope": "shared", "text": text})
        for text in self.world_store().search(query_embedding, top_k=top_k_world):
            results.append({"scope": "world", "text": text})
        return results

    def list_character_memory(self, character_id):
        return self.character_store(character_id).data

    def list_shared_memory(self):
        return self.shared_store().data

    def list_world_memory(self):
        return self.world_store().data

    @staticmethod
    def _safe_scope(scope):
        return "".join(c if c.isalnum() or c in {"_", "-"} else "_" for c in str(scope))[:120] or "shared"
