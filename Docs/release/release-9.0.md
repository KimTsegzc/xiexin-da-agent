# Release 9.0

Date: 2026-04-06

Tag: `V9.0`

一句话版本说明：完成 Prompt 工程化升级、欢迎语链路可观测与会话记忆治理，配套本地启动稳定性和 CI/CD 发版基线联调，形成可持续 prompt 迭代闭环。

## Scope

- release integration for `main`
- prompt engineering pipeline hardening
- welcome generation session memory isolation
- A/B/C random routing with ratio control
- debug observability from backend to frontend
- launcher reliability and hot-reload support
- CI gate local validation and release notes refresh

## Major Changes

1. Prompt 工程升级
- `Prompt/welcome.py` 从 A/B 扩展为 A/B/C，支持三路概率控制。
- 去重提示模板抽象到顶层，避免逻辑散落，便于后续 prompt tuning。
- 新增短期记忆拼接策略：记忆列表 + 常见开头规避，降低句式复读。

2. 欢迎语生成链路治理
- API 层统一生成欢迎语，Prompt 层只保留资产和策略。
- 引入 session 级用户记忆缓存：`Memory/user_specific/welcome_cache/<session_id>.jsonl`。
- welcome 请求返回可观测 debug payload（请求参数、分流、记忆、流式片段、延迟）。

3. 热更新能力
- 后端新增 welcome prompt 热加载（基于 `Prompt/welcome.py` mtime）。
- 修改欢迎语 prompt 后无需重启后端，下一次 `frontend-config` 请求可生效。
- 可通过 `XIEXIN_WELCOME_HOT_RELOAD` 控制开关。

4. 启动与联调稳定性
- `Launcher/Go_XIEXin.py` 增加启动互斥锁，避免重复启动相互抢占。
- 失败弹窗信息去噪，优先显示关键错误，降低 debug 干扰。
- Python I/O 编码设置增强，降低 Windows 场景日志乱码概率。

5. 仓库结构迁移（大树改动）
- 旧 `Gateway/*` 与旧 `Memo/*` 路径完成清理。
- 新目录统一为 `Backend/`、`Front/`、`Prompt/`、`apps/`、`Docs/`、`Memory/`。
- release 文档历史归档到 `Docs/release/`。

## Versioning

- root package version: `9.0.0`
- frontend package version: `9.0.0`
- git release target: `V9.0`

## CI/CD Validation (Local)

### CI Gate-equivalent checks

- Python dependency install: passed
- Python compile check (`orchestrator.py Backend apps Prompt`): passed
- Backend smoke import check: passed
- Frontend install + build (`Front/react-ui`): passed
- Secret gate regex scan (`sk-...`): no match in tracked files

### Notes on frontend CI in Windows

- 首次 `npm ci` 因 `esbuild.exe` 文件锁（EPERM）失败。
- 通过停止本地栈、清理 `node_modules`、重装依赖后构建通过。
- Linux CI runner 中通常不会遇到该锁文件问题。

### CD status

- GitHub workflow 文件已存在：
  - `.github/workflows/ci-gate.yml`
  - `.github/workflows/cd-deploy.yml`
- 本次为本地联调与发版准备，云端 CD 实际执行依赖 GitHub Actions push/tag 触发与远端密钥。

## Recommended Release Steps

1. Commit current V9.0 release set
2. Push to `main`
3. Create git tag `V9.0`
4. Observe CI Gate result in GitHub Actions
5. Confirm CD deploy health endpoint returns 200

## Known Risks

- welcome 去重目前仍以 prompt 约束为主，尚未加生成后强校验重采样。
- Windows 本地开发可能偶发 Node/esbuild 文件锁，需要先停前端进程再 `npm ci`。
- 热更新目前聚焦 `Prompt/welcome.py`，其他 Prompt 文件尚未纳入统一 watcher。
