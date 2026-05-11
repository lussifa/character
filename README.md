# Character AI Studio (Python)

<!-- codex write test -->

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

### 🎭 Multi-Character System
- Independent character profiles
- Goal / mood / state
- Relationship graph between characters

### 🎬 Conversation Orchestrator
- Speaker scheduling
- Multi-character dialogue generation
- Context fusion (memory + graph + world)

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
world_model.json              world state, events, and timeline
models/embedding/             local ONNX embedding model and tokenizer files
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

---

## License

AGPL-3.0 (aligned with original inspiration project)
