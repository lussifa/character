from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from .models import Character, ChatMessage, PromptTemplate, ModelConfig
from .schemas import CharacterCreate, MessageCreate, MemoryCreate
from .providers import call_model
from .onnx_embedder import ONNXEmbedder
from .vector_memory import VectorMemoryStore
from .memory_decider import decide_memory, decision_to_tier
from .memory_reviser import revise_memory
from .knowledge_graph import KnowledgeGraphStore
from .graph_extractor import extract_graph, apply_graph_extraction
from .graph_reasoner import GraphReasoner
from .llm_graph_reasoner import infer_graph_with_llm, apply_llm_inferences, llm_reasoning_context

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Character AI Studio")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

embedder = ONNXEmbedder()
vector_store = VectorMemoryStore()
graph_store = KnowledgeGraphStore()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/characters")
def create_character(data: CharacterCreate, db: Session = Depends(get_db)):
    char = Character(name=data.name, description=data.description)
    db.add(char)
    db.commit()
    return {"id": char.id}

@app.get("/characters")
def list_characters(db: Session = Depends(get_db)):
    return db.query(Character).all()

@app.post("/characters/{char_id}/chat")
async def chat(char_id: int, data: MessageCreate, db: Session = Depends(get_db)):
    character = db.query(Character).get(char_id)
    if not character:
        return {"error": "Character not found"}

    template = db.query(PromptTemplate).filter_by(is_default=True).first()
    model_config = db.query(ModelConfig).filter_by(is_default=True).first()

    if not template:
        template = PromptTemplate(
            name="default",
            template="You are {character_name}. Personality: {character_desc}\n\nMemory:\n{memory}\n\nUser:\n{user_input}",
            is_default=True,
        )
        db.add(template)
        db.commit()

    query_embedding = embedder.embed(data.content)
    relevant_memories = vector_store.search(query_embedding, top_k=5)
    memory_text = "\n".join(f"- {m}" for m in relevant_memories)

    graph_store.upsert_entity("user", "User", "person")
    graph_store.upsert_entity("current_character", character.name, "character", {"description": character.description or ""})

    rule_reasoner = GraphReasoner(graph_store)
    rule_reasoner.apply()
    rule_context = rule_reasoner.reasoning_context()

    llm_facts = await infer_graph_with_llm(graph_store, model_config=model_config)
    apply_llm_inferences(graph_store, llm_facts)
    llm_context = llm_reasoning_context(llm_facts, graph_store)

    graph_context = graph_store.context_for(["user", "current_character"], limit=30)

    cognitive_context = "\n".join([
        "Relevant vector memories:",
        memory_text or "- None",
        "",
        "Known graph facts:",
        graph_context or "- None",
        "",
        "Rule-based inferred facts:",
        rule_context or "- None",
        "",
        "LLM-inferred facts:",
        llm_context or "- None",
    ])

    prompt = template.template.format(
        character_name=character.name,
        character_desc=character.description or "",
        memory=cognitive_context,
        user_input=data.content,
    )

    system_prompt = f"You are roleplaying as {character.name}. Stay in character, keep continuity, use relevant memories, and respect known/inferred graph facts naturally."
    ai_reply = await call_model(prompt, system=system_prompt, model_config=model_config)

    db.add(ChatMessage(role="user", content=data.content, character_id=char_id))
    db.add(ChatMessage(role="assistant", content=ai_reply, character_id=char_id))

    decision = await decide_memory(data.content, ai_reply, model_config=model_config)
    if decision.action != "ignore":
        new_embedding = embedder.embed(decision.memory)
        conflict = vector_store.find_conflict(new_embedding, threshold=0.90)
        if conflict:
            revision = await revise_memory(conflict["text"], decision.memory, model_config=model_config)
            if revision.action == "replace":
                conflict["text"] = revision.revised_memory
                conflict["embedding"] = embedder.embed(revision.revised_memory).tolist()
                conflict["importance"] = max(conflict.get("importance", 0.5), revision.importance)
                conflict["tier"] = decision_to_tier(decision.action)
                vector_store._rewrite()
            elif revision.action == "merge":
                conflict["text"] = revision.revised_memory
                conflict["embedding"] = embedder.embed(revision.revised_memory).tolist()
                conflict["importance"] = max(conflict.get("importance", 0.5), revision.importance)
                vector_store._rewrite()
            elif revision.action == "delete":
                vector_store.data = [m for m in vector_store.data if m.get("memory_id") != conflict.get("memory_id")]
                vector_store._rewrite()
        else:
            vector_store.add(
                decision.memory,
                new_embedding,
                importance=decision.importance,
                source="ai_decision",
                tier=decision_to_tier(decision.action),
            )

    extraction = await extract_graph(data.content, ai_reply, model_config=model_config)
    apply_graph_extraction(graph_store, extraction)

    db.commit()
    return {"reply": ai_reply}

@app.get("/characters/{char_id}/messages")
def get_messages(char_id: int, db: Session = Depends(get_db)):
    return db.query(ChatMessage).filter_by(character_id=char_id).all()

@app.post("/characters/{char_id}/memory")
def add_memory(char_id: int, data: MemoryCreate, db: Session = Depends(get_db)):
    embedding = embedder.embed(data.content)
    vector_store.add(data.content, embedding, importance=0.7, source="manual", tier="long_term")
    return {"status": "ok"}

@app.get("/characters/{char_id}/memory")
def list_memory(char_id: int):
    return vector_store.data
