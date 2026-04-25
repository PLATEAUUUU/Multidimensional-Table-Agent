# interview-ai scaffold

AI 智能面试系统的工程化骨架，强调多 Agent 编排、可追踪审计、飞书多维表格持久化预留点，以及前端回合锁定与 WebSocket 重连机制。

## 目录

```text
.
├── app
│   ├── agents
│   ├── core
│   ├── memory
│   ├── skills
│   ├── tools
│   ├── config.py
│   └── main.py
├── configs/prompts
├── scripts
├── web
├── docker-compose.yml
└── requirements.txt
```

## 运行

### 后端

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端

```bash
cd web
npm install
npm run dev
```

### Docker Compose

```bash
docker compose up
```

## 说明

- 当前仓库只提供基类、占位实现与依赖关系，不包含具体业务逻辑。
- 所有 Prompt 从 `configs/prompts/` 加载，避免在代码中硬编码。
- 飞书多维表格持久化和内容安全拦截器均保留为可扩展占位。
