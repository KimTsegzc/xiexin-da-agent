# Release 9.1

Date: 2026-04-06

Tag: `V9.1`

一句话版本说明：修复 `soul.md` 在新目录结构下未参与系统提示词控制的问题，恢复全局人格/风格约束生效。

## Scope

- soul prompt path hotfix
- compatibility fallback for legacy layout
- version bump for backend and frontend

## Root Cause

- 在 V9.0 的目录迁移后，`Backend/settings.py` 里 `REPO_ROOT` 仍使用旧层级计算：
  - 旧实现：`Path(__file__).resolve().parents[2]`
- 这会把仓库根目录误算到上一级，导致 `Prompt/soul.md` 实际读取路径错误，最终系统提示词为空串。

## Fix

1. 修正仓库根目录计算
- 文件：`Backend/settings.py`
- 变更：`REPO_ROOT = Path(__file__).resolve().parents[1]`

2. 增加旧路径兼容回退
- 主路径：`Prompt/soul.md`
- 回退路径：`soul.md`（兼容历史布局）

## Impact

- `LLMProvider` 的 system message 会再次稳定加载 `soul.md`。
- 聊天人格、称呼、口吻等全局约束恢复有效。
- 改动后无需额外迁移数据，不影响 `welcome` 会话记忆目录。

## Validation

- Python compile check passed: `orchestrator.py Backend apps Prompt`
- `load_system_prompt()` 可读取到 `Prompt/soul.md` 内容（非空）
- Frontend build passed

## Versioning

- root package version: `9.1.0`
- frontend package version: `9.1.0`
- git release target: `V9.1`
