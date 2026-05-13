import json
import time
import hashlib
from pathlib import Path


class WorldModelStore:
    """Persistent world state with visibility-aware events.

    The store keeps objective world facts in one file, but every event can carry
    visibility metadata so each NPC only receives what they could plausibly know.
    """

    PUBLIC_VISIBILITIES = {"public", "world", "broadcast"}
    LOCAL_VISIBILITIES = {"local", "location"}
    PRIVATE_VISIBILITIES = {"private", "secret", "direct"}

    def __init__(self, path="world_model.json"):
        self.path = Path(path)
        if self.path.exists():
            self.world = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.world = {
                "state": {},
                "locations": {},
                "events": [],
                "dialogues": [],
                "knowledge_transfers": [],
                "timeline": [],
            }
        self._ensure_schema()

    def _ensure_schema(self):
        self.world.setdefault("state", {})
        self.world.setdefault("locations", {})
        self.world.setdefault("events", [])
        self.world.setdefault("dialogues", [])
        self.world.setdefault("knowledge_transfers", [])
        self.world.setdefault("timeline", [])

    def set_state(self, key, value, confidence=0.8, evidence=""):
        self.world["state"][key] = {
            "value": value,
            "confidence": float(max(0.0, min(1.0, confidence))),
            "evidence": evidence,
            "updated_at": time.time(),
        }
        self.save()

    def set_location(self, location_id, name=None, description="", metadata=None):
        location_id = str(location_id or "unknown").strip() or "unknown"
        existing = self.world.setdefault("locations", {}).get(location_id, {})
        self.world["locations"][location_id] = {
            "location_id": location_id,
            "name": name or existing.get("name") or location_id,
            "description": description or existing.get("description", ""),
            "metadata": metadata if isinstance(metadata, dict) else existing.get("metadata", {}),
            "updated_at": time.time(),
        }
        self.save()
        return self.world["locations"][location_id]

    def add_event(
        self,
        title,
        description,
        participants=None,
        location="",
        effects=None,
        confidence=0.8,
        visibility="public",
        observable_by=None,
        event_type="event",
    ):
        participants = [str(p) for p in (participants or []) if str(p).strip()]
        observable_by = [str(p) for p in (observable_by or []) if str(p).strip()]
        event_id = self._event_id(title, description, participants, location, visibility)
        event = {
            "event_id": event_id,
            "type": event_type or "event",
            "title": title,
            "description": description,
            "participants": participants,
            "location": location,
            "visibility": visibility or "public",
            "observable_by": observable_by,
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

    def add_knowledge_transfer(self, from_character_id, to_character_id, fact, method="direct_talk", event_id=""):
        item = {
            "from_character_id": from_character_id,
            "to_character_id": to_character_id,
            "fact": fact,
            "method": method,
            "event_id": event_id,
            "created_at": time.time(),
        }
        self.world.setdefault("knowledge_transfers", []).append(item)
        self.save()
        return item

    def record_dialogue(
        self,
        participants,
        content,
        location="",
        privacy="private",
        observable_by=None,
        title="NPC dialogue",
        memory_writes=None,
        confidence=0.9,
    ):
        participants = [str(p) for p in (participants or []) if str(p).strip()]
        observable_by = [str(p) for p in (observable_by or []) if str(p).strip()]
        if isinstance(content, list):
            normalized_content = content
            description = "\n".join(
                f"{line.get('speaker', 'unknown')}: {line.get('text', '')}" if isinstance(line, dict) else str(line)
                for line in content
            )
        else:
            normalized_content = str(content)
            description = str(content)

        event_id = self.add_event(
            title=title,
            description=description,
            participants=participants,
            location=location,
            confidence=confidence,
            visibility=privacy,
            observable_by=observable_by,
            event_type="dialogue",
        )
        dialogue = {
            "dialogue_id": event_id,
            "event_id": event_id,
            "participants": participants,
            "location": location,
            "privacy": privacy,
            "observable_by": observable_by,
            "content": normalized_content,
            "memory_writes": memory_writes or {},
            "created_at": time.time(),
        }
        if not any(d.get("dialogue_id") == event_id for d in self.world.setdefault("dialogues", [])):
            self.world["dialogues"].append(dialogue)
            self.save()
        return dialogue

    def context(self, limit_events=10):
        return self.context_for_character(None, None, limit_events=limit_events, include_private=True)

    def context_for_character(self, character_id, location=None, limit_events=10, include_private=False):
        lines = ["World state:"]
        for key, item in self.world.get("state", {}).items():
            lines.append(f"- {key}: {item.get('value')} (confidence={item.get('confidence', 0.0):.2f})")

        if location:
            loc = self.world.get("locations", {}).get(location)
            if loc:
                lines.append("Current location:")
                lines.append(f"- {loc.get('name', location)}: {loc.get('description', '')}")

        visible_events = self.visible_events_for(character_id, location, include_private=include_private)
        lines.append("Visible recent events:")
        for event in visible_events[-limit_events:]:
            lines.append(f"- {event.get('title')}: {event.get('description')}")
        if not visible_events:
            lines.append("- None")
        return "\n".join(lines)

    def visible_events_for(self, character_id, location=None, include_private=False):
        if include_private:
            return list(self.world.get("events", []))
        visible = []
        for event in self.world.get("events", []):
            if self._is_event_visible_to(event, character_id, location):
                visible.append(event)
        return visible

    def _is_event_visible_to(self, event, character_id, location=None):
        visibility = str(event.get("visibility", "public") or "public").lower()
        participants = set(event.get("participants") or [])
        observable_by = set(event.get("observable_by") or [])
        event_location = event.get("location") or ""

        if visibility in self.PUBLIC_VISIBILITIES:
            return True
        if character_id and character_id in participants:
            return True
        if character_id and character_id in observable_by:
            return True
        if visibility in self.LOCAL_VISIBILITIES and location and event_location == location:
            return True
        return False

    def _apply_effects(self, event):
        for effect in event.get("effects", []):
            if not isinstance(effect, dict):
                continue
            key = effect.get("key")
            value = effect.get("value")
            if key:
                self.set_state(key, value, effect.get("confidence", event.get("confidence", 0.8)), effect.get("evidence", event.get("title", "")))

    def save(self):
        self._ensure_schema()
        self.path.write_text(json.dumps(self.world, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _event_id(title, description, participants=None, location="", visibility="public"):
        raw = json.dumps(
            {
                "title": title,
                "description": description,
                "participants": participants or [],
                "location": location,
                "visibility": visibility,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]
