# XIEXin DA Agent

Version: 13.5.0

XIEXin DA Agent 是一个面向数据分析工作流的轻量 AI Agent 项目：后端提供流式 LLM 接口，前端提供桌面 / 移动 / 微信兼容聊天界面，部署链路基于 Ubuntu + systemd + nginx，并已接入基础 CI/CD。

## 当前主体架构

- `apps/api/server.py`：统一 HTTP 入口，提供 `/health`、`/api/frontend-config`、`/api/chat`、`/api/chat/stream`
- `Backend/features`：APP 功能层，负责会话上下文、互动状态等产品功能实现
- `Backend/runtime`：智能体运行时与技能编排
- `Backend/integrations`：LLM、搜索、邮件以及后续文件/TTS 等外部能力接入
- `Backend/settings.py`：运行时配置与 capability accessors
- `Prompt`：Prompt 工程目录（`soul.md` 与欢迎语生成）
- `Front/react-ui`：React + Vite 前端，支持桌面、移动默认端、微信端三套壳层
- `Deployer`：Ubuntu 部署脚本、systemd 模板、nginx 模板、健康检查
- `Launcher`：本地联调与快捷启动脚本
- `Docs`：版本记录、设计素材、发布说明与产品规划

## 当前功能

- 多模型切换，前端从后端读取可用模型与默认模型
- 聊天接口支持普通返回与 NDJSON 流式返回
- 移动端 / 微信端输入法稳定性治理
- 会话本地持久化与基础运行指标展示
- 头像互动、欢迎态 / 聊天态双状态界面
- `.env` 配置加载、Ubuntu 单机部署、GitHub Actions CI/CD

## 界面参考

![Hero](Docs/release/release-8.0/%E6%89%8B%E6%9C%BA%E7%AB%AFhero-page.jpg)

![Chat](Docs/release/release-8.0/%E6%89%8B%E6%9C%BA%E7%AB%AFchat-page.jpg)

## 目录速览

```text
.
├─ Backend/
│  ├─ features/         # APP 功能层（会话上下文、互动状态等）
│  ├─ runtime/          # 智能体编排层
│  ├─ integrations/     # 外部能力接入层
│  └─ settings.py       # 配置入口
├─ Prompt/               # Prompt 工程（soul.md / welcome.py）
├─ Front/react-ui/       # React 前端
├─ Deployer/             # Ubuntu 部署脚本与模板
├─ Launcher/             # 本地启动脚本
├─ Docs/                 # 版本、设计资料与 PRD
├─ apps/api/server.py     # HTTP 编排入口（主路径）
├─ orchestrator.py       # 兼容壳入口（保留旧启动链路）
└─ pyproject.toml        # Python 项目元数据
```

## 本地开发

### Backend

1. 在项目根创建 `.env`
2. 填写 `ALIYUN_BAILIAN_API_KEY`
3. 安装依赖并启动后端

### Frontend

在 `Front/react-ui` 下安装依赖后运行：

- `npm run dev`：本地开发
- `npm run build`：构建 `dist`
- `npm run preview`：预览构建结果

## 部署

推荐环境：Ubuntu 22.04 / 24.04，前端走 `8501`，后端走 `8766`，由 nginx 统一暴露 `80/443`。完整部署说明见 [Deployer/README.md](Deployer/README.md)。

## 发布说明

- 版本详情见 [Docs/release/release-13.5.md](Docs/release/release-13.5.md)
- 当前发布目标：`main` + tag `V13.5`