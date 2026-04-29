from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from .models import Character, ChatMessage, Memory, PromptTemplate
from .schemas import CharacterCreate, MessageCreate, MemoryCreate
from .prompt_engine import build_prompt
from .providers import call_model

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Character AI Studio")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
    memories = db.query(Memory).filter_by(character_id=char_id).all()
    template = db.query(PromptTemplate).filter_by(is_default=True).first()

    if not template:
        template = PromptTemplate(
            name="default",
            template="You are {character_name}. Personality: {character_desc}\nMemory:\n{memory}\nUser: {user_input}",
            is_default=True
        )
        db.add(template)
        db.commit()

    prompt = build_prompt(character, memories, data.content, template)
    ai_reply = await call_model(prompt)

    db.add(ChatMessage(role="user", content=data.content, character_id=char_id))
    db.add(ChatMessage(role="assistant", content=ai_reply, character_id=char_id))

    if len(data.content) > 30:
        db.add(Memory(content=data.content[:100], character_id=char_id))

    db.commit()
    return {"reply": ai_reply}

@app.get("/characters/{char_id}/messages")
def get_messages(char_id: int, db: Session = Depends(get_db)):
    return db.query(ChatMessage).filter_by(character_id=char_id).all()

@app.post("/characters/{char_id}/memory")
def add_memory(char_id: int, data: MemoryCreate, db: Session = Depends(get_db)):
    mem = Memory(content=data.content, character_id=char_id)
    db.add(mem)
    db.commit()
    return {"id": mem.id}

@app.get("/characters/{char_id}/memory")
def list_memory(char_id: int, db: Session = Depends(get_db)):
    return db.query(Memory).filter_by(character_id=char_id).all()
