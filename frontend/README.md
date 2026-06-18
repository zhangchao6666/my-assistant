# My Assistant Frontend

Vue 3 + Vite + TypeScript 的最小聊天前端。

## 开发运行

先启动后端服务，默认地址为 `http://127.0.0.1:8000`。

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器默认运行在 `http://localhost:5173`。

Vite 已配置代理：前端请求 `/api/chat` 会转发到后端的 `/chat`。
