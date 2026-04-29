from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .database import engine, Base, get_db
from .models import Character, ChatMessage, ModelConfig
from .schemas import CharacterCreate, MessageCreate, MemoryCreate
from .onnx_embedder import ONNXEmbedder
from .knowledge_graph import KnowledgeGraphStore
from .world_model import WorldModelStore
from .multi_character import MultiCharacterStore
from .scoped_memory import ScopedMemoryManager
from .conversation_orchestrator import orchestrate_conversation

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Character AI Studio")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

embedder = ONNXEmbedder()
scoped_memory = ScopedMemoryManager()
graph_store = KnowledgeGraphStore()
world_store = WorldModelStore()
multi_store = MultiCharacterStore()

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

def _safe_model_config(config: ModelConfig | None):
    if not config:
        return {
            "name": "default",
            "provider": "mock",
            "model": "mock-roleplay",
            "base_url": "",
            "api_key_set": False,
            "is_default": True,
        }
    return {
        "id": config.id,
        "name": config.name,
        "provider": config.provider,
        "model": config.model,
        "base_url": config.base_url,
        "api_key_set": bool(getattr(config, "api_key", "")),
        "is_default": config.is_default,
    }

@app.get("/model-config")
def get_model_config(db: Session = Depends(get_db)):
    config = db.query(ModelConfig).filter_by(is_default=True).first()
    return _safe_model_config(config)

@app.post("/model-config")
def save_model_config(data: ModelConfigRequest, db: Session = Depends(get_db)):
    db.query(ModelConfig).update({ModelConfig.is_default: False})
    config = db.query(ModelConfig).filter_by(name=data.name).first()
    if not config:
        config = ModelConfig(name=data.name)
        db.add(config)

    config.provider = data.provider
    config.model = data.model
    config.base_url = data.base_url
    if data.api_key:
        config.api_key = data.api_key
    config.is_default = data.is_default
    db.commit()
    db.refresh(config)
    return _safe_model_config(config)

@app.post("/characters")
def create_character(data: CharacterCreate, db: Session = Depends(get_db)):
    char = Character(name=data.name, description=data.description)
    db.add(char)
    db.commit()

    multi_store.upsert_character(
        character_id=f"character_{char.id}",
        name=char.name,
        persona=char.description or "",
        speaking_style="",
        goal="interact with the user",
        mood="neutral",
        location="unknown",
        status="active",
    )
    return {"id": char.id, "multi_character_id": f"character_{char.id}"}

@app.get("/characters")
def list_characters(db: Session = Depends(get_db)):
    return db.query(Character).all()

@app.post("/characters/{char_id}/chat")
async def chat(char_id: int, data: MessageCreate, db: Session = Depends(get_db)):
    character = db.query(Character).get(char_id)
    if not character:
        return {"error": "Character not found"}

    model_config = db.query(ModelConfig).filter_by(is_default=True).first()
    speaker_id = f"character_{char_id}"
    multi_store.upsert_character(
        character_id=speaker_id,
        name=character.name,
        persona=character.description or "",
        goal="interact with the user",
        mood="neutral",
        location="unknown",
        status="active",
    )

    result = await orchestrate_conversation(
        user_input=data.content,
        embedder=embedder,
        scoped_memory=scoped_memory,
        multi_store=multi_store,
        graph_store=graph_store,
        world_store=world_store,
        model_config=model_config,
        max_speakers=1,
        auto_simulate_world=True,
    )

    reply_text = "\n".join(f"{r.character_name}: {r.text}" for r in result.replies)
    db.add(ChatMessage(role="user", content=data.content, character_id=char_id))
    db.add(ChatMessage(role="assistant", content=reply_text, character_id=char_id))
    db.commit()

    return {
        "reply": reply_text,
        "replies": [r.__dict__ for r in result.replies],
        "scheduler": result.scheduler,
        "world_simulation": result.world_simulation,
    }

@app.post("/chat/multi")
async def multi_chat(data: MultiChatRequest, db: Session = Depends(get_db)):
    model_config = db.query(ModelConfig).filter_by(is_default=True).first()
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

@app.get("/characters/{char_id}/messages")
def get_messages(char_id: int, db: Session = Depends(get_db)):
    return db.query(ChatMessage).filter_by(character_id=char_id).all()

@app.post("/characters/{char_id}/memory")
def add_memory(char_id: int, data: MemoryCreate):
    embedding = embedder.embed(data.content)
    scoped_memory.add_character_memory(
        character_id=f"character_{char_id}",
        text=data.content,
        embedding=embedding,
        importance=0.7,
        source="manual",
        tier="long_term",
    )
    return {"status": "ok", "scope": f"character_{char_id}"}

@app.get("/characters/{char_id}/memory")
def list_memory(char_id: int):
    return scoped_memory.list_character_memory(f"character_{char_id}")

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
