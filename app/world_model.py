import json
import time
import hashlib
from pathlib import Path


class WorldModelStore:
    def __init__(self, path="world_model.json"):
        self.path = Path(path)
        if self.path.exists():
            self.world = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.world = {
                "state": {},
                "events": [],
                "timeline": [],
            }

    def set_state(self, key, value, confidence=0.8, evidence=""):
        self.world["state"][key] = {
            "value": value,
            "confidence": float(max(0.0, min(1.0, confidence))),
            "evidence": evidence,
            "updated_at": time.time(),
        }
        self.save()

    def add_event(self, title, description, participants=None, location="", effects=None, confidence=0.8):
        event_id = self._event_id(title, description)
        event = {
            "event_id": event_id,
            "title": title,
            "description": description,
            "participants": participants or [],
            "location": location,
            "effects": effects or [],
            "confidence": float(max(0.0, min(1.0, confidence))),
            "created_at": time.time(),
        }
        if not any(e.get("event_id") == event_id for e in self.world["events"]):
            self.world["events"].append(event)
            self.world["timeline"].append(event_id)
            self._apply_effects(event)
            self.save()
        return event_id

    def context(self, limit_events=10):
        lines = ["World state:"]
        for key, item in self.world.get("state", {}).items():
            lines.append(f"- {key}: {item.get('value')} (confidence={item.get('confidence', 0.0):.2f})")

        lines.append("Recent events:")
        by_id = {e["event_id"]: e for e in self.world.get("events", [])}
        for event_id in self.world.get("timeline", [])[-limit_events:]:
            event = by_id.get(event_id)
            if event:
                lines.append(f"- {event['title']}: {event['description']}")
        return "\n".join(lines)

    def _apply_effects(self, event):
        for effect in event.get("effects", []):
            if not isinstance(effect, dict):
                continue
            key = effect.get("key")
            value = effect.get("value")
            if key:
                self.set_state(key, value, effect.get("confidence", event.get("confidence", 0.8)), effect.get("evidence", event.get("title", "")))

    def save(self):
        self.path.write_text(json.dumps(self.world, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _event_id(title, description):
        raw = f"{title}\n{description}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]
