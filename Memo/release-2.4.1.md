# Release 2.4.1

建议 tag: `v2.4.1`

## 补丁摘要

1. 配置源从 `config.json` 迁移到环境变量和 `.env` 文件，避免把 API Key 放进仓库。
2. 后端新增 `Gateway.Back.settings`，统一管理模型、系统提示词和生成参数。
3. `Gateway.Back.llm_provider` 改为读取 `Settings`，保留原有流式事件协议，不改前端消费方式。
4. `Gateway.Back.__init__` 改成惰性导入，减少包导入时的副作用和配置依赖。
5. 新增 `.env.example` 作为本地配置模板，并补充 `.gitignore`，默认忽略 `.env` 与构建产物。
6. 启动脚本 `Launcher/start_frontend_silent.ps1` 与 `Launcher/stop_frontend.ps1` 支持 `-PythonOverride`，可显式绕过 exe，便于排查打包与运行环境差异。
7. `Launcher/README.md` 同步说明新的启动优先级和停止逻辑。

## 适合写进 annotated tag 的文案

release: v2.4.1

- migrate runtime config from config.json to .env / environment variables
- add Gateway.Back.settings for centralized runtime settings
- switch llm_provider to settings-based configuration loading
- make Gateway.Back lazy-import LLMProvider to reduce import side effects
- support -PythonOverride in launcher start/stop scripts
- add .env.example and tighten ignore rules for local secrets/build artifacts

## 发布注意事项

1. 当前工作区仍有未提交的素材、文档和其他改动，发版前应白名单挑选本次补丁文件。
2. 不建议在当前 HEAD 直接创建 `v2.4.1`，因为 HEAD 仍指向 `v2.4.0` 对应提交；应先提交 2.4.1 发布内容，再打 tag。