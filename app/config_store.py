import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FileModelConfig:
    name: str = "default"
    provider: str = "mock"
    model: str = "mock-roleplay"
    base_url: str = ""
    api_key: str = ""
    is_default: bool = True


class ModelConfigStore:
    def __init__(self, path="config/model_config.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def get(self) -> FileModelConfig:
        if not self.path.exists():
            config = FileModelConfig()
            self.save(config)
            return config
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return FileModelConfig(**{**asdict(FileModelConfig()), **data})

    def save(self, config: FileModelConfig) -> FileModelConfig:
        self.path.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
        return config

    def update(self, data: dict) -> FileModelConfig:
        current = self.get()
        merged = asdict(current)
        for key in ["name", "provider", "model", "base_url", "is_default"]:
            if key in data:
                merged[key] = data[key]
        if data.get("api_key"):
            merged["api_key"] = data["api_key"]
        return self.save(FileModelConfig(**merged))


def safe_model_config(config: FileModelConfig) -> dict:
    return {
        "name": config.name,
        "provider": config.provider,
        "model": config.model,
        "base_url": config.base_url,
        "api_key_set": bool(config.api_key),
        "is_default": config.is_default,
    }
