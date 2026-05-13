# Character AI Studio (Python)

一个本地优先的 **多角色 AI 世界引擎**，使用 Python + FastAPI 实现。  
这个项目已经不再是简单的单角色聊天，而是一个包含 **多 NPC、作用域记忆、知识图谱、世界状态、事件时间线、对话编排、可见性控制、私有记忆传播** 的运行时系统。基于当前代码，项目支持按角色隔离记忆、按地点和可见性限制信息、记录世界事件和秘密对话，并通过 API 进行角色和世界状态的持续演化。fileciteturn36file0turn8file0turn9file0turn21file0

---

## 1. 当前项目已经实现了什么

### 1.1 多角色运行时

项目内已经有独立的角色存储，角色包含：

- `character_id`
- `name`
- `persona`
- `speaking_style`
- `goal`
- `mood`
- `location`
- `status`
- `current_action`

同时支持角色关系维护，以及按地点查看“附近可见角色”。这意味着现在已经可以表达“npc1 在酒馆巡逻，npc2 在后巷放风，npc3 正在低声交谈”这一类状态。fileciteturn9file0

### 1.2 作用域记忆

项目的记忆系统已经分为：

- `character`：角色私有记忆
- `shared`：共享记忆
- `world`：世界记忆

底层使用本地 JSONL 存储，每个角色都有独立的记忆文件，不会天然共享。检索时会优先取当前角色记忆，再混合共享记忆和世界记忆。fileciteturn12file0turn33file0

### 1.3 世界状态与事件系统

世界模型已经支持：

- `state`
- `locations`
- `events`
- `dialogues`
- `knowledge_transfers`
- `timeline`

每个事件支持 `visibility` 和 `observable_by`。因此你现在可以区分：

- 公共事件
- 仅当前地点可见的事件
- 私密事件
- 只有特定角色能观察到的事件

这正是实现“NPC 不共享记忆，除非他们参与、观察或被告知”的基础。fileciteturn8file0

### 1.4 多角色对话编排

对话编排器会：

- 调度当前发言角色
- 为当前角色检索私有记忆
- 组合当前角色能看到的世界上下文
- 生成符合角色身份的回复
- 将新回复写回角色记忆
- 抽取世界事件和图谱信息
- 记录对话对其他参与者产生的“听到的记忆”

当前版本的重要变化是：角色回复时不再默认拿全局所有 NPC 状态，而是只拿 **自己可见的内容**。Prompt 中也明确限制“不能使用角色不该知道的信息”。fileciteturn21file0

### 1.5 手工世界控制、Seed 导入与前端控制台

当前已经支持通过 API：

- 创建地点
- 写入世界事件
- 写入秘密对话
- 导入完整种子世界 `seed`

同时首页前端也已经扩展成 **世界控制台**，可以在 UI 中直接：

- 查看当前 NPC 状态
- 查看世界统计和最近事件
- 配置模型
- 创建或更新 NPC
- 保存角色关系
- 导入 seed
- 创建地点、世界事件、秘密对话
- 查看当前 world JSON

`/world/load-seed` 会重建运行时文件，并一次性导入地点、角色、关系、世界事件、对话和初始记忆。仓库中还提供了示例种子文件 `examples/worldx_seed.json`、`static/worldx_seed.json` 和示例导入脚本 `scripts/load_seed_example.py`。fileciteturn36file0turn32file0turn43file0turn44file0

---

## 2. 安装

### 2.1 Python 环境

建议 Python 3.10+。

创建虚拟环境并安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

项目当前依赖的核心组件包括：

- `fastapi`
- `uvicorn`
- `pydantic`
- `httpx`
- `jinja2`
- `onnxruntime`
- `transformers`
- `numpy` fileciteturn25file0

Windows PowerShell 可以使用：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 3. 启动

项目的主入口是 `app/main.py`，这是一个 FastAPI 应用。fileciteturn11file0

启动命令：

```bash
uvicorn app.main:app --reload
```

启动后默认访问地址：

- UI: `http://127.0.0.1:8000`
- Swagger 文档: `http://127.0.0.1:8000/docs` fileciteturn11file0

首页会渲染 `templates/index.html`，静态资源由 `/static` 提供。前端主逻辑在 `static/app.js`，样式在 `static/style.css`。fileciteturn43file0turn44file0turn45file0

---

## 4. 模型配置

### 4.1 配置文件位置

模型配置保存在：

```text
config/model_config.json
```

默认配置字段包括：

- `name`
- `provider`
- `model`
- `base_url`
- `api_key`
- `is_default` fileciteturn40file0

### 4.2 当前支持的 provider

当前代码支持 3 种模型提供方：

- `mock`
- `openai_compatible`
- `ollama` fileciteturn41file0turn40file0

### 4.3 配置方式

你可以通过 API 配置：

- `GET /model-config`
- `POST /model-config` fileciteturn36file0

前端“设置与世界控制台”里也可以直接修改这些字段并保存。fileciteturn43file0turn44file0

示例：

#### OpenAI 兼容接口

```json
{
  "name": "default",
  "provider": "openai_compatible",
  "model": "gpt-4o",
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-xxx",
  "is_default": true
}
```

#### Ollama

```json
{
  "name": "default",
  "provider": "ollama",
  "model": "llama3",
  "base_url": "http://localhost:11434",
  "api_key": "",
  "is_default": true
}
```

#### Mock

```json
{
  "name": "default",
  "provider": "mock",
  "model": "mock-roleplay",
  "base_url": "",
  "api_key": "",
  "is_default": true
}
```

另外，`providers.py` 里也支持从环境变量读取配置，例如 `PROVIDER`、`MODEL_NAME`、`OPENAI_BASE_URL`、`OPENAI_API_KEY`、`OLLAMA_URL`。fileciteturn41file0

---

## 5. Embedding 模型配置

项目的向量记忆依赖本地 ONNX embedding 模型。默认目录是：

```text
models/embedding/
```

至少需要以下文件之一：

- `model-int8.onnx`
- `model.onnx`

同时建议包含：

- `config.json`
- `tokenizer.json`
- `tokenizer_config.json`
- `special_tokens_map.json` fileciteturn29file0

如果目录里没有可用的 ONNX 模型，应用无法正常启动向量记忆能力。README 当前也保留了如何下载或导出 ONNX 模型的说明。fileciteturn29file0

你也可以通过环境变量覆盖默认模型目录：

```bash
export EMBEDDING_MODEL_DIR=/path/to/embedding-model
```

Windows PowerShell：

```powershell
$env:EMBEDDING_MODEL_DIR="D:\models\embedding"
```

---

## 6. 运行时文件结构

当前运行时数据主要落在这些文件里：

```text
config/model_config.json      模型配置
multi_characters.json         角色和关系
memory/*.jsonl                作用域记忆
knowledge_graph.json          知识图谱
world_model.json              世界状态、事件、对话、时间线
models/embedding/             本地向量模型
examples/worldx_seed.json     示例 seed 世界
static/worldx_seed.json       前端可直接加载的示例 seed
```

这些文件全部是本地文件存储，当前运行路径不依赖 SQLite。fileciteturn29file0turn8file0turn9file0turn43file0

---

## 7. 主要 API

### 7.1 角色相关

- `POST /characters`
- `GET /characters`
- `POST /characters/{character_id}/chat`
- `POST /characters/{character_id}/memory`
- `GET /characters/{character_id}/memory`
- `POST /multi-characters`
- `GET /multi-characters`
- `PATCH /multi-characters/{character_id}/state`
- `POST /multi-characters/relationships` fileciteturn36file0

### 7.2 对话相关

- `POST /chat/multi`：多角色对话入口。fileciteturn36file0

### 7.3 世界相关

- `POST /world/locations`
- `POST /world/events`
- `POST /world/dialogues`
- `POST /world/load-seed`
- `GET /world` fileciteturn36file0

### 7.4 其他

- `GET /graph`
- `GET /memory/shared`
- `GET /memory/world` fileciteturn36file0

---

## 8. 前端怎么用

### 8.1 首页结构

启动后访问 `http://127.0.0.1:8000`，页面大致分成两块：

- 左侧：NPC 列表 + 世界速览 + 最近世界事件
- 右侧：聊天区
- 右上角：`刷新世界` 和 `设置`

点击 `设置` 后会打开“设置与世界控制台”。fileciteturn43file0turn44file0

### 8.2 推荐上手顺序

建议你第一次启动时按这个顺序使用：

1. 打开“设置与世界控制台”
2. 在 **LLM API 配置** 里选择 `mock` / `openai_compatible` / `ollama`
3. 点击 **导入示例 worldx_seed**
4. 点击 **导入 Seed**
5. 观察左侧 NPC 列表和世界速览是否刷新
6. 关闭设置，在聊天框输入一条消息开始运行世界

这是当前最快的体验方式。fileciteturn43file0turn44file0

### 8.3 前端控制台能做什么

前端目前已经可以直接完成这些操作：

- 保存模型配置
- 创建或更新 NPC
- 编辑 NPC 的位置和当前行为
- 创建角色关系
- 导入 seed
- 从前端加载示例 seed
- 创建地点
- 创建世界事件
- 创建秘密对话
- 查看当前 `world` JSON
- 刷新世界状态和 NPC 列表。fileciteturn43file0turn44file0

### 8.4 导入示例世界

在设置面板中：

1. 点击 **导入示例 worldx_seed**
2. 文本框会自动填入示例 seed JSON
3. 点击 **导入 Seed**

前端读取的是：

```text
/static/worldx_seed.json
```

后端实际调用的是：

```text
POST /world/load-seed
```

导入完成后，前端会自动刷新 NPC 列表和 world 预览。fileciteturn43file0turn44file0

### 8.5 手工创建秘密对话

在“秘密对话 / 手工对话”区域里：

- `participants` 填参与者 ID，逗号分隔，例如 `npc3,npc4`
- `privacy` 选择 `secret`
- `content` 填 JSON 数组
- `memory_writes` 填每个参与者应该获得的私有记忆 JSON

点击“创建对话”后，前端会调用 `/world/dialogues`，并在成功后刷新 world 视图。fileciteturn43file0turn44file0

---

## 9. 最小使用流程

### 9.1 创建角色

```json
POST /multi-characters
{
  "character_id": "npc1",
  "name": "雷恩",
  "persona": "谨慎守卫",
  "goal": "维持秩序",
  "mood": "警惕",
  "location": "tavern",
  "status": "active",
  "current_action": "在酒馆巡逻"
}
```

### 9.2 发起多角色对话

```json
POST /chat/multi
{
  "content": "敌人来了怎么办？",
  "max_speakers": 2,
  "auto_simulate_world": true
}
```

### 9.3 手工写入秘密对话

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

### 9.4 导入 seed 世界

```json
POST /world/load-seed
{
  "seed": {
    "locations": [],
    "characters": [],
    "relationships": [],
    "world_events": [],
    "dialogues": [],
    "character_memories": {}
  },
  "reset_graph": false
}
```

或者直接运行脚本：

```bash
python scripts/load_seed_example.py
```

默认会导入：

```text
examples/worldx_seed.json
``` fileciteturn36file0turn32file0

---

## 10. 测试与示例

仓库当前有两个可直接运行的脚本：

```bash
python scripts/smoke_check.py
python scripts/visibility_smoke_check.py
```

其中 `visibility_smoke_check.py` 会验证：

- 酒馆本地事件只对酒馆中的 NPC 可见
- 后巷秘密对话不会泄露给不在场角色
- 参与秘密对话的 NPC 会获得对应记忆
- 不在场的 NPC 不会凭空共享那段信息。fileciteturn26file0turn31file0

---

## 11. 当前已经实现的“核心能力”总结

从现在这个分支的代码来看，项目已经具备这些关键能力：

1. **多 NPC 持续状态管理**  
   角色有目标、情绪、位置、当前行为和关系。fileciteturn9file0

2. **角色私有记忆隔离**  
   每个角色独立存储记忆，不自动共享。fileciteturn12file0turn33file0

3. **世界事件可见性控制**  
   事件支持 public/local/private/secret 等可见范围。fileciteturn8file0

4. **秘密对话与知识传播**  
   只有参与者或观察者能知道秘密对话，交流后才会形成知识传播记录。fileciteturn8file0turn21file0

5. **多角色对话编排**  
   支持选择发言人、组合上下文、生成多角色回复。fileciteturn21file0

6. **结构化 seed 导入**  
   可以一键加载一个完整小世界作为初始运行状态。fileciteturn36file0turn32file0

7. **前端世界控制台**  
   支持通过 UI 管理角色、关系、地点、事件、秘密对话和 seed。fileciteturn43file0turn44file0turn45file0

8. **本地优先运行**  
   模型配置、角色、世界、记忆全部落本地文件，便于调试和迭代。fileciteturn40file0turn29file0

---

## 12. 当前还没有做的部分

为了避免预期过高，也要明确现在还没做的点：

- 还没有“一句话自动生成世界”的接口；当前是 **先准备 seed，再导入**。fileciteturn36file0turn32file0
- 还没有更完整的自动 seed 校验器和迁移器；当前导入逻辑偏工程内使用。fileciteturn36file0
- 还没有更系统的单元测试体系，当前以脚本式 smoke check 为主。fileciteturn26file0turn31file0
- 还没有前端上的“从自然语言生成 seed”入口；当前前端做的是结构化导入和手工控制。fileciteturn43file0turn44file0
- 知识图谱与世界模拟已经接入流程，但复杂度和稳定性仍取决于你接入的模型质量与 Prompt 调整。fileciteturn21file0turn41file0

---

## 13. License

AGPL-3.0。fileciteturn29file0
