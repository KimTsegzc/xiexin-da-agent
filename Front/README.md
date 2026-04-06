# Front README

当前 `Front` 已收敛为单一前端栈：React + Vite。

## 目录

```text
Front/
├─ react-ui/
│  ├─ src/
│  ├─ public/
│  ├─ wechat/index.html
│  ├─ index.html
│  ├─ vite.config.js
│  ├─ package.json
│  └─ package-lock.json
└─ README.md
```

## 运行方式

在 `Front/react-ui` 下执行：

```bash
npm install
npm run dev
```

默认入口：
- http://127.0.0.1:8501/

微信入口：
- http://127.0.0.1:8501/wechat/

## 与后端接口

- `GET /api/frontend-config`
- `POST /api/chat`
- `POST /api/chat/stream`

后端主入口在 `apps/api/server.py`，仓库根 `orchestrator.py` 为兼容壳。

## 说明

- 本目录已移除历史遗留的 Streamlit、Taro 与参考素材实现，仅保留 React + Vite 主链路。
- `node_modules` 与 `dist` 为本地/构建产物，不应提交到仓库。