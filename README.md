# My Assistant

一个本地运行的个人 AI 助手项目，包含 FastAPI 后端和 Vue 3 前端。后端提供聊天与天气查询接口，聊天能力默认通过 Ollama 暴露的 OpenAI 兼容接口调用本地大模型；前端提供一个简洁的聊天界面，并通过 Vite 代理访问后端服务。

## 功能特性

- AI 对话：前端发送多轮消息，后端调用本地 LLM 返回回复。
- 天气查询：通过 `wttr.in` 获取指定城市的当前天气。
- 前后端分离：后端使用 FastAPI，前端使用 Vue 3 + Vite + TypeScript。
- 本地模型优先：默认连接 `http://localhost:11434/v1`，适合配合 Ollama 使用。

## 技术栈

- 后端：Python 3.14、FastAPI、Uvicorn、OpenAI Python SDK、Requests
- 前端：Vue 3、Vite、TypeScript
- 包管理：后端推荐使用 `uv`，前端使用 `npm`

## 项目结构

```text
.
├── app/
│   ├── api/              # FastAPI 路由
│   ├── models/           # 请求与响应模型
│   ├── services/         # LLM 与天气服务
│   ├── tools/            # 工具封装
│   └── main.py           # 后端入口
├── frontend/
│   ├── src/              # Vue 前端源码
│   ├── package.json      # 前端依赖与脚本
│   └── vite.config.ts    # Vite 配置与 API 代理
├── pyproject.toml        # 后端项目配置
├── uv.lock               # 后端锁文件
└── README.md
```

## 环境准备

请先确认本机已安装：

- Python 3.14+
- uv
- Node.js 与 npm
- Ollama

后端聊天服务默认使用 Ollama 的 OpenAI 兼容接口：

```text
http://localhost:11434/v1
```

代码中默认模型名为 `qwen3.6`。启动前请确保 Ollama 中已有对应模型，或者在 `app/services/llm.py` 中把 `model` 改成你本机已安装的模型名称。

## 启动后端

在项目根目录执行：

```bash
uv sync
uv run uvicorn app.main:app --reload
```

后端默认运行在：

```text
http://127.0.0.1:8000
```

打开接口文档：

```text
http://127.0.0.1:8000/docs
```

## 启动前端

另开一个终端执行：

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在：

```text
http://localhost:5173
```

Vite 已配置代理：前端请求 `/api/chat` 会转发到后端的 `/chat` 接口。

## API 示例

### 健康检查

```bash
curl http://127.0.0.1:8000/
```

### 聊天

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}]}"
```

响应示例：

```json
{
  "reply": "你好！有什么我可以帮你的吗？"
}
```

### 天气查询

GET：

```bash
curl "http://127.0.0.1:8000/weather?city=Shanghai"
```

POST：

```bash
curl -X POST http://127.0.0.1:8000/weather \
  -H "Content-Type: application/json" \
  -d "{\"city\":\"Shanghai\"}"
```

响应示例：

```json
{
  "city": "Shanghai",
  "weather": "Partly cloudy",
  "temp": "26 ℃"
}
```

## 常见问题

### 前端发送消息失败

请确认：

- 后端已启动并运行在 `http://127.0.0.1:8000`。
- Ollama 已启动。
- `app/services/llm.py` 中的模型名存在于本机 Ollama。

### 天气接口返回失败

天气接口依赖外部服务 `wttr.in`，需要可访问互联网。如果网络不可用或外部服务异常，接口可能返回失败。

## 构建前端

```bash
cd frontend
npm run build
```

构建产物会生成在 `frontend/dist` 目录。
