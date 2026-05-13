from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config_store import ModelConfigStore, safe_model_config
from .onnx_embedder import ONNXEmbedder
from .knowledge_graph import KnowledgeGraphStore
from .world_model import WorldModelStore
from .multi_character import MultiCharacterStore
from .scoped_memory import ScopedMemoryManager
from .conversation_orchestrator import orchestrate_conversation

app = FastAPI(title="Character AI Studio")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

embedder = ONNXEmbedder()
scoped_memory = ScopedMemoryManager()
graph_store = KnowledgeGraphStore()
world_store = WorldModelStore()
multi_store = MultiCharacterStore()
model_config_store = ModelConfigStore()


class MultiCharacterCreate(BaseModel):
    character_id: str
    name: str
    persona: str = ""
    speaking_style: str = ""
    goal: str = ""
    mood: str = "neutral"
    location: str = "unknown"
    status: str = "active"
    current_action: str = "idle"


class CharacterStateUpdate(BaseModel):
    goal: str | None = None
    mood: str | None = None
    location: str | None = None
    status: str | None = None
    current_action: str | None = None


class RelationshipCreate(BaseModel):
    source_id: str
    target_id: str
    relation: str
    attitude: str = "neutral"
    confidence: float = 0.8


class MultiChatRequest(BaseModel):
    content: str
    max_speakers: int = 2
    auto_simulate_world: bool = True


class ModelConfigRequest(BaseModel):
    name: str = "default"
    provider: str = "mock"
    model: str = "mock-roleplay"
    base_url: str = ""
    api_key: str = ""
    is_default: bool = True


class WorldLocationRequest(BaseModel):
    location_id: str
    name: str | None = None
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ManualWorldEventRequest(BaseModel):
    title: str
    description: str
    participants: list[str] = Field(default_factory=list)
    location: str = ""
    effects: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.8
    visibility: str = "public"
    observable_by: list[str] = Field(default_factory=list)
    event_type: str = "manual"


class DialogueLine(BaseModel):
    speaker: str
    text: str


class ManualDialogueRequest(BaseModel):
    participants: list[str]
    location: str = ""
    privacy: str = "private"
    observable_by: list[str] = Field(default_factory=list)
    title: str = "NPC dialogue"
    content: list[DialogueLine] | str
    memory_writes: dict[str, list[str]] = Field(default_factory=dict)
    confidence: float = 0.9


class SeedLoadRequest(BaseModel):
    seed: dict[str, Any]
    reset_graph: bool = False


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/model-config")
def get_model_config():
    return safe_model_config(model_config_store.get())


@app.post("/model-config")
def save_model_config(data: ModelConfigRequest):
    config = model_config_store.update(data.model_dump())
    return safe_model_config(config)


@app.post("/chat/multi")
async def multi_chat(data: MultiChatRequest):
    model_config = model_config_store.get()
    result = await orchestrate_conversation(
        user_input=data.content,
        embedder=embedder,
        scoped_memory=scoped_memory,
        multi_store=multi_store,
        graph_store=graph_store,
        world_store=world_store,
        model_config=model_config,
        max_speakers=data.max_speakers,
        auto_simulate_world=data.auto_simulate_world,
    )
    return {
        "replies": [r.__dict__ for r in result.replies],
        "scheduler": result.scheduler,
        "world_simulation": result.world_simulation,
        "cognitive_context": result.cognitive_context,
    }


@app.post("/characters")
def create_character(data: MultiCharacterCreate):
    world_store.set_location(data.location, name=data.location)
    return multi_store.upsert_character(**data.model_dump())


@app.get("/characters")
def list_characters():
    return multi_store.list_characters()


@app.post("/characters/{character_id}/chat")
async def chat(character_id: str, data: MultiChatRequest):
    character = multi_store.get_character(character_id)
    if not character:
        return {"error": "Character not found"}
    model_config = model_config_store.get()
    result = await orchestrate_conversation(
        user_input=data.content,
        embedder=embedder,
        scoped_memory=scoped_memory,
        multi_store=multi_store,
        graph_store=graph_store,
        world_store=world_store,
        model_config=model_config,
        max_speakers=1,
        auto_simulate_world=data.auto_simulate_world,
    )
    return {
        "reply": "\n".join(f"{r.character_name}: {r.text}" for r in result.replies),
        "replies": [r.__dict__ for r in result.replies],
        "scheduler": result.scheduler,
        "world_simulation": result.world_simulation,
        "cognitive_context": result.cognitive_context,
    }


@app.post("/characters/{character_id}/memory")
def add_memory(character_id: str, data: dict):
    content = str(data.get("content", "")).strip()
    if not content:
        return {"error": "content is required"}
    embedding = embedder.embed(content)
    scoped_memory.add_character_memory(
        character_id=character_id,
        text=content,
        embedding=embedding,
        importance=float(data.get("importance", 0.7)),
        source="manual",
        tier=str(data.get("tier", "long_term")),
    )
    return {"status": "ok", "scope": f"character:{character_id}"}


@app.get("/characters/{character_id}/memory")
def list_memory(character_id: str):
    return scoped_memory.list_character_memory(character_id)


@app.post("/multi-characters")
def create_multi_character(data: MultiCharacterCreate):
    world_store.set_location(data.location, name=data.location)
    return multi_store.upsert_character(**data.model_dump())


@app.get("/multi-characters")
def list_multi_characters():
    return multi_store.list_characters()


@app.patch("/multi-characters/{character_id}/state")
def update_multi_character_state(character_id: str, data: CharacterStateUpdate):
    if data.location:
        world_store.set_location(data.location, name=data.location)
    updated = multi_store.update_state(character_id, **data.model_dump())
    if not updated:
        return {"error": "Character not found"}
    return updated


@app.post("/multi-characters/relationships")
def set_relationship(data: RelationshipCreate):
    return multi_store.set_relationship(**data.model_dump())


@app.post("/world/locations")
def upsert_world_location(data: WorldLocationRequest):
    return world_store.set_location(**data.model_dump())


@app.post("/world/events")
def add_world_event(data: ManualWorldEventRequest):
    event_id = world_store.add_event(**data.model_dump())
    return {"status": "ok", "event_id": event_id}


@app.post("/world/dialogues")
def add_world_dialogue(data: ManualDialogueRequest):
    payload = data.model_dump()
    if isinstance(payload["content"], list):
        payload["content"] = [line for line in payload["content"]]
    dialogue = world_store.record_dialogue(**payload)

    for character_id, memories in payload.get("memory_writes", {}).items():
        for memory in memories or []:
            text = str(memory).strip()
            if not text:
                continue
            embedding = embedder.embed(text)
            scoped_memory.add_character_memory(
                character_id=character_id,
                text=text,
                embedding=embedding,
                importance=0.8,
                source="manual_dialogue",
                tier="long_term",
            )

    participants = payload.get("participants", [])
    content = payload.get("content")
    if isinstance(content, list):
        transcript = "\n".join(f"{item.get('speaker', 'unknown')}: {item.get('text', '')}" for item in content)
    else:
        transcript = str(content)

    for listener_id in participants:
        if listener_id in payload.get("memory_writes", {}):
            continue
        heard_memory = f"You heard this dialogue at {payload.get('location') or 'unknown'}:\n{transcript}".strip()
        embedding = embedder.embed(heard_memory)
        scoped_memory.add_character_memory(
            character_id=listener_id,
            text=heard_memory,
            embedding=embedding,
            importance=0.65,
            source="manual_dialogue_heard",
            tier="short_term",
        )

    return {"status": "ok", "dialogue": dialogue}


@app.post("/world/load-seed")
def load_seed(data: SeedLoadRequest):
    stats = _apply_seed(data.seed, reset_graph=data.reset_graph)
    return {"status": "ok", **stats}


@app.get("/memory/shared")
def list_shared_memory():
    return scoped_memory.list_shared_memory()


@app.get("/memory/world")
def list_world_memory():
    return scoped_memory.list_world_memory()


@app.get("/world")
def get_world():
    return world_store.world


@app.get("/graph")
def get_graph():
    return graph_store.graph


def _apply_seed(seed: dict[str, Any], reset_graph: bool = False) -> dict[str, Any]:
    scoped_memory.reset_all()

    multi_store.data = {"characters": {}, "relationships": []}
    multi_store.save()

    world_store.world = {
        "state": {},
        "locations": {},
        "events": [],
        "dialogues": [],
        "knowledge_transfers": [],
        "timeline": [],
    }
    world_store.save()

    if reset_graph:
        graph_store.graph = {"entities": [], "relations": []}
        graph_store.save()

    locations = seed.get("locations", []) if isinstance(seed.get("locations", []), list) else []
    characters = seed.get("characters", []) if isinstance(seed.get("characters", []), list) else []
    relationships = seed.get("relationships", []) if isinstance(seed.get("relationships", []), list) else []
    world_events = seed.get("world_events", []) if isinstance(seed.get("world_events", []), list) else []
    dialogues = seed.get("dialogues", []) if isinstance(seed.get("dialogues", []), list) else []
    character_memories = seed.get("character_memories", {}) if isinstance(seed.get("character_memories", {}), dict) else {}
    shared_memories = seed.get("shared_memories", []) if isinstance(seed.get("shared_memories", []), list) else []
    world_memories = seed.get("world_memories", []) if isinstance(seed.get("world_memories", []), list) else []

    for item in locations:
        if not isinstance(item, dict):
            continue
        location_id = str(item.get("location_id", "")).strip()
        if not location_id:
            continue
        world_store.set_location(
            location_id=location_id,
            name=item.get("name"),
            description=str(item.get("description", "")),
            metadata=item.get("metadata", {}) if isinstance(item.get("metadata", {}), dict) else {},
        )

    for item in characters:
        if not isinstance(item, dict):
            continue
        character_id = str(item.get("character_id", "")).strip()
        name = str(item.get("name", "")).strip()
        if not character_id or not name:
            continue
        location = str(item.get("location", "unknown") or "unknown")
        world_store.set_location(location, name=location)
        multi_store.upsert_character(
            character_id=character_id,
            name=name,
            persona=str(item.get("persona", "")),
            speaking_style=str(item.get("speaking_style", "")),
            goal=str(item.get("goal", "")),
            mood=str(item.get("mood", "neutral")),
            location=location,
            status=str(item.get("status", "active")),
            current_action=str(item.get("current_action", "idle")),
        )

    for item in relationships:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id", "")).strip()
        target_id = str(item.get("target_id", "")).strip()
        relation = str(item.get("relation", "")).strip()
        if not source_id or not target_id or not relation:
            continue
        multi_store.set_relationship(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            attitude=str(item.get("attitude", "neutral")),
            confidence=float(item.get("confidence", 0.8)),
        )

    for item in world_events:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        description = str(item.get("description", "")).strip()
        if not title or not description:
            continue
        world_store.add_event(
            title=title,
            description=description,
            participants=item.get("participants", []) if isinstance(item.get("participants", []), list) else [],
            location=str(item.get("location", "")),
            effects=item.get("effects", []) if isinstance(item.get("effects", []), list) else [],
            confidence=float(item.get("confidence", 0.8)),
            visibility=str(item.get("visibility", "public")),
            observable_by=item.get("observable_by", []) if isinstance(item.get("observable_by", []), list) else [],
            event_type=str(item.get("event_type", "seed")),
        )

    for item in dialogues:
        if not isinstance(item, dict):
            continue
        participants = item.get("participants", []) if isinstance(item.get("participants", []), list) else []
        content = item.get("content", "")
        if isinstance(content, list):
            content = [line for line in content if isinstance(line, dict)]
        dialogue = world_store.record_dialogue(
            participants=participants,
            content=content,
            location=str(item.get("location", "")),
            privacy=str(item.get("privacy", "private")),
            observable_by=item.get("observable_by", []) if isinstance(item.get("observable_by", []), list) else [],
            title=str(item.get("title", "NPC dialogue")),
            memory_writes=item.get("memory_writes", {}) if isinstance(item.get("memory_writes", {}), dict) else {},
            confidence=float(item.get("confidence", 0.9)),
        )
        for character_id, memories in dialogue.get("memory_writes", {}).items():
            for memory in memories or []:
                _store_character_memory(character_id, memory, source="seed_dialogue", tier="long_term", importance=0.8)

    for character_id, memories in character_memories.items():
        if not isinstance(memories, list):
            continue
        for memory in memories:
            _store_character_memory(character_id, memory, source="seed", tier="long_term", importance=0.75)

    for memory in shared_memories:
        _store_shared_memory(memory, source="seed_shared", tier="long_term", importance=0.7)

    for memory in world_memories:
        _store_world_memory(memory, source="seed_world", tier="long_term", importance=0.7)

    return {
        "locations": len(world_store.world.get("locations", {})),
        "characters": len(multi_store.data.get("characters", {})),
        "relationships": len(multi_store.data.get("relationships", [])),
        "events": len(world_store.world.get("events", [])),
        "dialogues": len(world_store.world.get("dialogues", [])),
        "character_memory_scopes": len(character_memories),
    }


def _store_character_memory(character_id: str, memory: Any, source: str, tier: str, importance: float):
    text = str(memory).strip()
    if not text:
        return
    embedding = embedder.embed(text)
    scoped_memory.add_character_memory(
        character_id=character_id,
        text=text,
        embedding=embedding,
        importance=importance,
        source=source,
        tier=tier,
    )


def _store_shared_memory(memory: Any, source: str, tier: str, importance: float):
    text = str(memory).strip()
    if not text:
        return
    embedding = embedder.embed(text)
    scoped_memory.add_shared_memory(
        text=text,
        embedding=embedding,
        importance=importance,
        source=source,
        tier=tier,
    )


def _store_world_memory(memory: Any, source: str, tier: str, importance: float):
    text = str(memory).strip()
    if not text:
        return
    embedding = embedder.embed(text)
    scoped_memory.add_world_memory(
        text=text,
        embedding=embedding,
        importance=importance,
        source=source,
        tier=tier,
    )
