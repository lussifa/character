import json
import time
from pathlib import Path


class MultiCharacterStore:
    def __init__(self, path="multi_characters.json"):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {"characters": {}, "relationships": []}

    def upsert_character(
        self,
        character_id,
        name,
        persona="",
        speaking_style="",
        goal="",
        mood="neutral",
        location="unknown",
        status="active",
        current_action="idle",
    ):
        now = time.time()
        existing = self.data["characters"].get(character_id, {})
        self.data["characters"][character_id] = {
            "character_id": character_id,
            "name": name,
            "persona": persona or existing.get("persona", ""),
            "speaking_style": speaking_style or existing.get("speaking_style", ""),
            "state": {
                "goal": goal or existing.get("state", {}).get("goal", ""),
                "mood": mood or existing.get("state", {}).get("mood", "neutral"),
                "location": location or existing.get("state", {}).get("location", "unknown"),
                "status": status or existing.get("state", {}).get("status", "active"),
                "current_action": current_action or existing.get("state", {}).get("current_action", "idle"),
            },
            "created_at": existing.get("created_at", now),
            "updated_at": now,
        }
        self.save()
        return self.data["characters"][character_id]

    def update_state(self, character_id, **updates):
        char = self.data["characters"].get(character_id)
        if not char:
            return None
        state = char.setdefault("state", {})
        for key in ["goal", "mood", "location", "status", "current_action"]:
            if key in updates and updates[key] is not None:
                state[key] = updates[key]
        char["updated_at"] = time.time()
        self.save()
        return char

    def set_relationship(self, source_id, target_id, relation, attitude="neutral", confidence=0.8):
        item = {
            "source_id": source_id,
            "target_id": target_id,
            "relation": relation,
            "attitude": attitude,
            "confidence": float(max(0.0, min(1.0, confidence))),
            "updated_at": time.time(),
        }
        for rel in self.data["relationships"]:
            if rel["source_id"] == source_id and rel["target_id"] == target_id:
                rel.update(item)
                self.save()
                return rel
        self.data["relationships"].append(item)
        self.save()
        return item

    def get_character(self, character_id):
        return self.data["characters"].get(character_id)

    def list_characters(self):
        return list(self.data["characters"].values())

    def characters_at_location(self, location, exclude_character_id=None):
        result = []
        for char in self.data["characters"].values():
            state = char.get("state", {})
            if state.get("location") == location:
                if exclude_character_id and char.get("character_id") == exclude_character_id:
                    continue
                result.append(char)
        return result

    def visible_characters_for(self, character_id):
        current = self.get_character(character_id)
        if not current:
            return []
        location = current.get("state", {}).get("location")
        return self.characters_at_location(location, exclude_character_id=character_id)

    def character_context(self, character_id, visible_only=False):
        char = self.get_character(character_id)
        if not char:
            return ""
        state = char.get("state", {})
        lines = [
            f"Character: {char.get('name')} ({character_id})",
            f"Persona: {char.get('persona', '')}",
            f"Speaking style: {char.get('speaking_style', '')}",
            f"Goal: {state.get('goal', '')}",
            f"Mood: {state.get('mood', 'neutral')}",
            f"Location: {state.get('location', 'unknown')}",
            f"Current action: {state.get('current_action', 'idle')}",
            f"Status: {state.get('status', 'active')}",
        ]

        related = [
            r for r in self.data["relationships"]
            if r["source_id"] == character_id or r["target_id"] == character_id
        ]
        if related:
            lines.append("Relationships:")
            for rel in related:
                lines.append(
                    f"- {rel['source_id']} {rel['relation']} {rel['target_id']} attitude={rel.get('attitude', 'neutral')}"
                )

        visible = self.visible_characters_for(character_id)
        if visible:
            lines.append("Visible nearby characters:")
            for other in visible:
                other_state = other.get("state", {})
                lines.append(
                    f"- {other.get('name')} at {other_state.get('location')} doing {other_state.get('current_action', 'unknown')}"
                )

        if visible_only:
            return "\n".join(lines)

        return "\n".join(lines)

    def group_context(self):
        lines = []
        for cid in self.data["characters"]:
            lines.append(self.character_context(cid))
        return "\n\n".join(lines)

    def choose_speakers(self, requested_ids=None, max_speakers=2):
        if requested_ids:
            return [cid for cid in requested_ids if cid in self.data["characters"]][:max_speakers]
        active = [
            cid for cid, c in self.data["characters"].items()
            if c.get("state", {}).get("status", "active") == "active"
        ]
        return active[:max_speakers]

    def save(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
