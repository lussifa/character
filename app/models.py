from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, Float
from .database import Base

class Character(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)

class ChatMessage(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String)
    content = Column(Text)
    character_id = Column(Integer, ForeignKey("characters.id"))

class Memory(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    character_id = Column(Integer, ForeignKey("characters.id"))
    embedding_json = Column(Text, default="")
    importance = Column(Float, default=0.5)
    source = Column(String, default="manual")

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    template = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)

class ModelConfig(Base):
    __tablename__ = "model_configs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    provider = Column(String, nullable=False, default="mock")
    model = Column(String, nullable=False, default="mock-roleplay")
    base_url = Column(String, default="")
    api_key = Column(Text, default="")
    is_default = Column(Boolean, default=False)
