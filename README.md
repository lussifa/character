# Character AI Studio (Python)

A local-first **multi-character AI world engine** built in Python.

This project started as a LettuceAI-inspired system, but has evolved into a full **multi-character cognitive system** with:

- Scoped memory (per-character memory isolation)
- Knowledge graph + reasoning
- World model + simulation
- Multi-character orchestration (no agents required)
- Pure file-based runtime storage, no SQLite required

---

## 🚀 Core Features

### 🧠 Memory System
- Vector memory (ONNX embeddings)
- Scoped memory (character / shared / world)
- Memory conflict resolution + revision

### 🕸️ Knowledge Graph
- Entity + relationship extraction
- Rule-based reasoning
- LLM-based reasoning

### 🌍 World Model
- Persistent world state
- Event extraction from dialogue
- Timeline tracking
- AI-driven world simulation
- Visibility-aware events and dialogues
- Private NPC memory that only spreads through direct interaction

### 🎭 Multi-Character System
- Independent character profiles
- Goal / mood / state
- Current action tracking per NPC
- Relationship graph between characters

### 🎬 Conversation Orchestrator
- Speaker scheduling
- Multi-character dialogue generation
- Context fusion (memory + graph + world)
- Per-NPC cognition scoped to visible world context instead of full global context

### ⚙️ Model Config
- UI-based LLM API configuration
- Stored in `config/model_config.json`
- Supports `mock`, `openai_compatible`, and `ollama`

---

## 🧪 How to Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- UI: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

---

## 🧠 Embedding ONNX Model Setup

This project uses a local ONNX embedding model for vector memory.

By default, the app looks for the embedding model here:

```text
models/embedding/
```

The directory must contain:

```text
models/embedding/
  model-int8.onnx          preferred, quantized ONNX model
  # or model.onnx          fallback FP32 ONNX model
  config.json              recommended, helps AutoTokenizer identify model type
  tokenizer.json           usually enough for Xenova tokenizers
  tokenizer_config.json    recommended
  special_tokens_map.json  recommended
```

Optional tokenizer vocabulary files may also appear, depending on the model:

```text
vocab.txt
vocab.json
merges.txt
sentencepiece.bpe.model
spiece.model
```

For `Xenova/paraphrase-multilingual-MiniLM-L12-v2`, it is normal if there is no `vocab.txt`. If `tokenizer.json` exists, copy it together with `tokenizer_config.json`, `special_tokens_map.json`, and `config.json`.

The app loads `model-int8.onnx` first. If it does not exist, it tries `model.onnx`.

### Option A: Download a ready-made ONNX embedding model

Recommended quick choices from Hugging Face:

- `Xenova/all-MiniLM-L6-v2` — small English embedding model
- `Xenova/paraphrase-multilingual-MiniLM-L12-v2` — multilingual model, usable for Chinese/English mixed text

Typical file mapping:

```text
Hugging Face repo file                 Local file
onnx/model_quantized.onnx              models/embedding/model-int8.onnx
# or onnx/model.onnx                   models/embedding/model.onnx
config.json                            models/embedding/config.json
tokenizer.json                         models/embedding/tokenizer.json
tokenizer_config.json                  models/embedding/tokenizer_config.json
special_tokens_map.json                models/embedding/special_tokens_map.json
```

If the downloaded ONNX file is named `model_quantized.onnx`, rename it to:

```text
model-int8.onnx
```

If the downloaded ONNX file is named `model.onnx`, keep it as:

```text
model.onnx
```

### Option B: Export your own ONNX embedding model

For Chinese-heavy usage, a BGE-style embedding model is usually better. Example source model candidates:

- `BAAI/bge-small-zh-v1.5`
- `BAAI/bge-base-zh-v1.5`
- `BAAI/bge-m3`

Export it to ONNX using Hugging Face/Optimum, then place the exported ONNX model and tokenizer files into:

```text
models/embedding/
```

The final directory must still contain either:

```text
model-int8.onnx
```

or:

```text
model.onnx
```

### Custom model directory

You can override the default model directory with:

```bash
export EMBEDDING_MODEL_DIR=/path/to/embedding-model
```

Windows PowerShell:

```powershell
$env:EMBEDDING_MODEL_DIR="D:\\models\\embedding"
```

---

## 📁 Runtime Storage

```text
config/model_config.json      LLM provider/model/API configuration
multi_characters.json         multi-character profiles and relationships
memory/*.jsonl                scoped vector memories
knowledge_graph.json          entity and relationship graph
world_model.json              world state, events, dialogues, and timeline
models/embedding/             local ONNX embedding model and tokenizer files
examples/worldx_seed.json     example seed world for private-NPC-memory scenarios
```

SQLite is no longer required by the runtime path.

---

## 🧪 Quick Test Flow

### 1. Configure embedding model

Download or export an ONNX embedding model and put it under:

```text
models/embedding/
```

The app will fail to start if neither `model-int8.onnx` nor `model.onnx` exists.

### 2. Configure LLM model in UI

Use the left-side **LLM API 配置** panel.

Examples:

```text
provider: openai_compatible
model: gpt-4o
base_url: https://api.openai.com/v1
api_key: sk-...
```

```text
provider: ollama
model: llama3
base_url: http://localhost:11434
```

### 3. 创建角色

POST `/multi-characters`

```json
{
  "character_id": "char_a",
  "name": "艾琳",
  "persona": "冷静剑士",
  "goal": "保护用户",
  "mood": "警惕"
}
```

### 4. 多角色对话

POST `/chat/multi`

```json
{
  "content": "敌人来了怎么办？",
  "max_speakers": 2,
  "auto_simulate_world": true
}
```

### 5. 验证 NPC 私有记忆不共享

运行现有冒烟脚本：

```bash
python scripts/smoke_check.py
```

运行新增可见性脚本：

```bash
python scripts/visibility_smoke_check.py
```

预期输出：

```text
visibility_smoke_check_ok
```

该脚本会验证：

- npc1 能看到自己所在酒馆的本地事件
- npc1 看不到 npc3 和 npc4 的秘密对话
- npc3 能看到自己参与的秘密对话
- npc4 会收到对话后的私有记忆
- npc1 不会因为世界里存在秘密事件就自动获得那段记忆

### 6. 使用手工 API 注入世界状态

你可以手工设置地点：

```json
POST /world/locations
{
  "location_id": "alley",
  "name": "后巷",
  "description": "偏僻、适合密谈"
}
```

你也可以手工写入秘密对话：

```json
POST /world/dialogues
{
  "participants": ["npc3", "npc4"],
  "location": "alley",
  "privacy": "secret",
  "observable_by": [],
  "title": "后巷密谈",
  "content": [
    {"speaker": "npc3", "text": "今晚别去钟楼，捕快已经盯上那里了。"},
    {"speaker": "npc4", "text": "那账本怎么办？"},
    {"speaker": "npc3", "text": "先藏在旧井下面。"}
  ],
  "memory_writes": {
    "npc3": ["我告诉了npc4钟楼不安全，账本藏在旧井下面"],
    "npc4": ["npc3说钟楼不安全", "npc3说账本藏在旧井下面"]
  }
}
```

### 7. 示例种子世界

仓库里提供了一个示例文件：

```text
examples/worldx_seed.json
```

它包含：

- 多个地点
- 4 个 NPC 的起始位置和当前行为
- 公共事件与秘密事件
- 一段只有参与者才知道的秘密对话
- 每个角色各自的初始记忆

---

## 🧠 Architecture Overview

```text
User Input
   ↓
Conversation Orchestrator
   ↓
Speaker Scheduler
   ↓
Per-character Memory (Scoped)
   ↓
Graph + Reasoning
   ↓
World State + Simulation
   ↓
Multi-character Responses
```

---

## ⚠️ Notes

- This system is not a simple chatbot.
- It is a **multi-character world simulation engine**.
- Behavior stability requires prompt tuning and iteration.
- API keys are stored locally in `config/model_config.json`; do not commit your real config file to a public repository.
- ONNX embedding model files are large and should normally not be committed to Git. Keep them in local runtime storage or use Git LFS.
- The new visibility model prevents NPCs from automatically sharing secret knowledge; only participation, observation, or explicit transfer should spread facts.

---

## License

AGPL-3.0 (aligned with original inspiration project)
