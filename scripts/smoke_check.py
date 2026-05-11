import asyncio
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config_store import FileModelConfig
from app.conversation_orchestrator import orchestrate_conversation
from app.knowledge_graph import KnowledgeGraphStore
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


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        old_cwd = os.getcwd()
        os.chdir(tmp)
        try:
            multi_store = MultiCharacterStore("multi_characters.json")
            scoped_memory = ScopedMemoryManager("memory")
            graph_store = KnowledgeGraphStore("knowledge_graph.json")
            world_store = WorldModelStore("world_model.json")

            multi_store.upsert_character(
                character_id="char_a",
                name="艾琳",
                persona="冷静剑士",
                goal="保护用户",
                mood="警惕",
            )
            multi_store.upsert_character(
                character_id="char_b",
                name="洛恩",
                persona="谨慎斥候",
                goal="观察敌人",
                mood="紧张",
            )
            multi_store.set_relationship("char_a", "char_b", "trusts", "friendly", 0.8)

            result = await orchestrate_conversation(
                user_input="敌人正在接近城门，我们该怎么办？",
                embedder=FakeEmbedder(),
                scoped_memory=scoped_memory,
                multi_store=multi_store,
                graph_store=graph_store,
                world_store=world_store,
                model_config=FileModelConfig(provider="mock", model="mock-roleplay"),
                max_speakers=2,
                auto_simulate_world=False,
            )
        finally:
            os.chdir(old_cwd)

    assert result.replies, "expected at least one mock reply"
    assert result.scheduler, "expected scheduler context"
    print("smoke_check_ok")


if __name__ == "__main__":
    asyncio.run(main())
