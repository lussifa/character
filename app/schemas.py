from pydantic import BaseModel

class CharacterCreate(BaseModel):
    name: str
    description: str = ""

class MessageCreate(BaseModel):
    content: str

class MemoryCreate(BaseModel):
    content: str
