import os
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.multi_character import MultiCharacterStore
from app.scoped_memory import ScopedMemoryManager
from app.world_model import WorldModelStore


class FakeEmbedder:
    def embed(self, text: str) -> np.ndarray:
        values = np.zeros(8, dtype=np.float32)
        for index, char in enumerate(text.encode("utf-8")):
            values[index % len(values)] += float(char)
        norm = np.linalg.norm(values)
        if norm == 0:
            values[0] = 1.0
            norm = 1.0
        return values / norm


def assert_contains(items, expected_substring, message):
    haystack = "\n".join(str(item) for item in items)
    assert expected_substring in haystack, message


def main():
    embedder = FakeEmbedder()
    with tempfile.TemporaryDirectory() as tmp:
        old_cwd = os.getcwd()
        os.chdir(tmp)
        try:
            multi_store = MultiCharacterStore("multi_characters.json")
            scoped_memory = ScopedMemoryManager("memory")
            world_store = WorldModelStore("world_model.json")

            world_store.set_location("tavern", name="酒馆", description="镇民收集消息的地方")
            world_store.set_location("alley", name="后巷", description="偏僻、适合密谈")

            multi_store.upsert_character(
                character_id="npc1",
                name="雷恩",
                persona="守卫",
                goal="维持秩序",
                mood="警惕",
                location="tavern",
                current_action="在酒馆巡逻",
            )
            multi_store.upsert_character(
                character_id="npc2",
                name="维克",
                persona="线人",
                goal="跟踪可疑商人",
                mood="紧张",
                location="alley",
                current_action="在后巷放风",
            )
            multi_store.upsert_character(
                character_id="npc3",
                name="玛拉",
                persona="情报贩子",
                goal="藏好账本",
                mood="谨慎",
                location="alley",
                current_action="低声交谈",
            )
            multi_store.upsert_character(
                character_id="npc4",
                name="欧文",
                persona="走私客",
                goal="躲避捕快",
                mood="不安",
                location="alley",
                current_action="和玛拉密谈",
            )

            world_store.add_event(
                title="酒馆里有人谈论失踪商人",
                description="镇民公开议论失踪商人的去向。",
                participants=["npc1"],
                location="tavern",
                visibility="local",
            )
            world_store.record_dialogue(
                participants=["npc3", "npc4"],
                location="alley",
                privacy="secret",
                observable_by=[],
                title="后巷密谈",
                content=[
                    {"speaker": "npc3", "text": "账本先藏在旧井下面。"},
                    {"speaker": "npc4", "text": "明白，我不会告诉别人。"},
                ],
                memory_writes={
                    "npc3": ["我告诉了npc4账本藏在旧井下面"],
                    "npc4": ["npc3说账本藏在旧井下面"],
                },
            )

            for cid, facts in {
                "npc3": ["我告诉了npc4账本藏在旧井下面"],
                "npc4": ["npc3说账本藏在旧井下面"],
            }.items():
                for fact in facts:
                    scoped_memory.add_character_memory(
                        character_id=cid,
                        text=fact,
                        embedding=embedder.embed(fact),
                        importance=0.8,
                        source="seed",
                        tier="long_term",
                    )

            npc1_context = world_store.context_for_character("npc1", location="tavern")
            npc3_context = world_store.context_for_character("npc3", location="alley")
            npc1_memory = scoped_memory.list_character_memory("npc1")
            npc4_memory = scoped_memory.list_character_memory("npc4")
            visible_to_npc1 = world_store.visible_events_for("npc1", location="tavern")
            visible_to_npc3 = world_store.visible_events_for("npc3", location="alley")

        finally:
            os.chdir(old_cwd)

    assert "失踪商人" in npc1_context, "npc1 should see tavern local event"
    assert "后巷密谈" not in npc1_context, "npc1 should not see secret alley dialogue"
    assert "后巷密谈" in npc3_context, "npc3 should see dialogue they participated in"
    assert not npc1_memory, "npc1 should not receive private dialogue memory"
    assert_contains(npc4_memory, "账本藏在旧井下面", "npc4 should receive dialogue memory")
    assert all(event.get("title") != "后巷密谈" for event in visible_to_npc1), "npc1 visible events leaked secret dialogue"
    assert any(event.get("title") == "后巷密谈" for event in visible_to_npc3), "npc3 should see own secret dialogue event"
    print("visibility_smoke_check_ok")


if __name__ == "__main__":
    main()
