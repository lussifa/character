from dataclasses import dataclass


@dataclass
class Character:
    name: str
    description: str = ""
    id: int | None = None


@dataclass
class ChatMessage:
    role: str
    content: str
    character_id: int | None = None
    id: int | None = None


@dataclass
class Memory:
    content: str
    character_id: int | None = None
    embedding_json: str = ""
    importance: float = 0.5
    source: str = "manual"
    id: int | None = None


@dataclass
class PromptTemplate:
    name: str
    template: str
    is_default: bool = False
    id: int | None = None


@dataclass
class ModelConfig:
    name: str = "default"
    provider: str = "mock"
    model: str = "mock-roleplay"
    base_url: str = ""
    api_key: str = ""
    is_default: bool = False
    id: int | None = None
