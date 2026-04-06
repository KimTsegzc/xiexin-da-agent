# Release 8.0

Date: 2026-04-05

Tag: `V8.0`

一句话版本说明：项目完成一次面向内测发布的集成收敛，架构说明、部署链路、CI/CD、前端发布方式与密钥治理全部统一到当前可持续迭代的基线。

## Scope

- release integration for `main`
- root documentation consolidation
- frontend dist-based deployment baseline
- CI gate + CD deployment workflow
- secret cleanup and `.env` standardization
- current architecture snapshot for mobile-first conversational UI

## Current Architecture Snapshot

### Backend

- `orchestrator.py` 作为统一入口，负责健康检查、前端配置下发、普通聊天、流式聊天
- `Gateway/Back/settings.py` 作为运行时配置入口，只认环境变量 / `.env`
- `Gateway/Back/llm_provider.py` 负责模型调用、流式事件、性能指标
- `Gateway/Back/__init__.py` 保持 `LLMProvider` 对外导出

### Frontend

- React + Vite 双入口：默认入口 + 微信入口
- 桌面、移动默认端、微信端三套壳层已拆分
- 会话持久化、设置面板、模型切换、流式渲染已模块化
- 当前发布模式改为构建 `dist` 后用 `npm run preview` 承载

### Deployment

- Ubuntu 单机部署
- `systemd` 托管 backend / frontend
- `nginx` 统一暴露 `80/443`
- backend 绑定 `127.0.0.1:8766`
- frontend 绑定 `127.0.0.1:8501`

### CI/CD

- GitHub Actions `CI Gate`：Python 编译检查、后端 smoke check、Node 安装、前端构建、基础 secret gate
- GitHub Actions `CD Deploy`：push 后通过 SSH 到腾讯云执行 `Deployer/pull_and_start.sh`

## Main Changes Since 6.0

1. 文档收敛
   - 删除过时的 `Architect.md`
   - 根 `readme.md` 重写为当前真实架构与功能说明
   - 使用 `Docs/release/release-8.0/` 中的界面图作为发布参考

2. 配置与安全治理
   - 移除 `config.json` 作为运行时配置回退
   - 统一改为 `.env` / 环境变量
   - 清理 `ali_test.py` 中的明文 key 写法
   - release 基线明确要求云端与本地都使用新轮换密钥

3. 部署链路治理
   - 对齐 backend 端口到 `8766`
   - 前端从 dev server 切换到 build + preview 方式
   - 部署脚本、systemd、nginx、健康检查、README 已全部同步

4. 工程化补齐
   - 新增基础 CI gate
   - 新增腾讯云 CD workflow
   - 初步形成 push → CI → CD → health check 的闭环

## Versioning

- root package version: `8.0.0`
- frontend package version: `8.0.0`
- git release target: `V8.0`

## Known Status

- 项目当前适合小范围内测与快速迭代，不以容器化和大规模弹性部署为目标
- 移动端 / 微信端输入法链路已显著好于早期版本，但仍建议持续真机回归
- CD 已具备自动化基础能力，但仍建议后续补充回滚与分环境策略

## Suggested Next Step After V8.0

1. 将 `CI Gate` 设为 required check
2. 为 `main` 增加 branch protection
3. 拆分 preview 与正式静态托管模式
4. 给 CD 增加失败回滚和通知
5. 继续清理历史实验性文档与遗留脚本