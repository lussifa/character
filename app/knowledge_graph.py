import json
import time
from pathlib import Path


class KnowledgeGraphStore:
    def __init__(self, path="knowledge_graph.json"):
        self.path = Path(path)
        if self.path.exists():
            self.graph = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.graph = {"entities": {}, "relations": []}

    def upsert_entity(self, entity_id, name, entity_type="unknown", attributes=None):
        now = time.time()
        existing = self.graph["entities"].get(entity_id, {})
        merged_attrs = existing.get("attributes", {})
        merged_attrs.update(attributes or {})
        self.graph["entities"][entity_id] = {
            "entity_id": entity_id,
            "name": name,
            "type": entity_type or existing.get("type", "unknown"),
            "attributes": merged_attrs,
            "created_at": existing.get("created_at", now),
            "updated_at": now,
        }
        self.save()

    def add_relation(self, source_id, relation, target_id, confidence=0.8, evidence=""):
        item = {
            "source_id": source_id,
            "relation": relation,
            "target_id": target_id,
            "confidence": float(max(0.0, min(1.0, confidence))),
            "evidence": evidence,
            "created_at": time.time(),
        }
        for rel in self.graph["relations"]:
            if rel["source_id"] == source_id and rel["relation"] == relation and rel["target_id"] == target_id:
                rel["confidence"] = max(rel.get("confidence", 0.0), item["confidence"])
                rel["evidence"] = item["evidence"] or rel.get("evidence", "")
                self.save()
                return
        self.graph["relations"].append(item)
        self.save()

    def query_entity(self, entity_id):
        entity = self.graph["entities"].get(entity_id)
        relations = [r for r in self.graph["relations"] if r["source_id"] == entity_id or r["target_id"] == entity_id]
        return {"entity": entity, "relations": relations}

    def context_for(self, entity_ids, limit=20):
        lines = []
        for entity_id in entity_ids:
            data = self.query_entity(entity_id)
            entity = data["entity"]
            if entity:
                lines.append(f"Entity: {entity['name']} ({entity['type']})")
                for key, value in entity.get("attributes", {}).items():
                    lines.append(f"- {key}: {value}")
            for rel in data["relations"][:limit]:
                src = self.graph["entities"].get(rel["source_id"], {}).get("name", rel["source_id"])
                tgt = self.graph["entities"].get(rel["target_id"], {}).get("name", rel["target_id"])
                lines.append(f"- {src} {rel['relation']} {tgt}")
        return "\n".join(lines[:limit])

    def save(self):
        self.path.write_text(json.dumps(self.graph, ensure_ascii=False, indent=2), encoding="utf-8")
