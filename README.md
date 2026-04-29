# Character AI Studio (Python)

A local-first **multi-character AI world engine** built in Python.

This project started as a LettuceAI-inspired system, but has evolved into a full **multi-character cognitive system** with:

- Scoped memory (per-character memory isolation)
- Knowledge graph + reasoning
- World model + simulation
- Multi-character orchestration (no agents required)

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

### 🎬 Conversation Orchestrator (核心)
- Speaker scheduling (谁说话)
- Multi-character dialogue generation
- Context fusion (memory + graph + world)

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

## 🧪 Quick Test Flow

### 1. 创建角色

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

### 2. 多角色对话

POST `/chat/multi`

```json
{
  "content": "敌人来了怎么办？",
  "max_speakers": 2
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

---

## License

AGPL-3.0 (aligned with original inspiration project)
