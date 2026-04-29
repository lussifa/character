from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .config_store import FileModelConfig, ModelConfigStore, safe_model_config
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

class CharacterStateUpdate(BaseModel):
    goal: str | None = None
    mood: str | None = None
    location: str | None = None
    status: str | None = None

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

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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
    }

@app.post("/characters")
def create_character(data: MultiCharacterCreate):
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
    return multi_store.upsert_character(**data.model_dump())

@app.get("/multi-characters")
def list_multi_characters():
    return multi_store.list_characters()

@app.patch("/multi-characters/{character_id}/state")
def update_multi_character_state(character_id: str, data: CharacterStateUpdate):
    updated = multi_store.update_state(character_id, **data.model_dump())
    if not updated:
        return {"error": "Character not found"}
    return updated

@app.post("/multi-characters/relationships")
def set_relationship(data: RelationshipCreate):
    return multi_store.set_relationship(**data.model_dump())

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
