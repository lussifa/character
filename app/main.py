from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from .models import Character, ChatMessage, Memory
from .schemas import CharacterCreate, MessageCreate, MemoryCreate

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Character AI Studio")

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <body>
        <h2>Character AI Studio</h2>
        <p>UI v1 ready.</p>
        <ul>
            <li><a href=\"/docs\">API Docs</a></li>
        </ul>
    </body>
    </html>
    """

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
def chat(char_id: int, data: MessageCreate, db: Session = Depends(get_db)):
    msg = ChatMessage(role="user", content=data.content, character_id=char_id)
    db.add(msg)

    reply = ChatMessage(role="assistant", content=f"Echo: {data.content}", character_id=char_id)
    db.add(reply)

    db.commit()
    return {"reply": reply.content}

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
