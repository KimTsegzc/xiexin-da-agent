# Release 14.0

Date: 2026-04-12

Tag: `V14.0`

一句话版本说明：正式上线图片/文件上传分析能力，修正 omni 模型切换链路，并补齐移动端聊天上传入口。

## Scope

- 前端聊天支持上传图片与文件，上传后先落到后端 shared_space 再进入对话链路
- 后端新增 `/api/uploads` 接口，统一保存附件元数据并在 direct chat 中注入图片/文本上下文
- 上传场景默认切换到 `qwen3-omni-flash`，修正因模型名大小写错误导致的 `modelnotfound`
- 修复 multipart 单文件上传时 `Cannot be converted to bool.` 异常
- 移动端 / 微信端聊天输入框恢复上传按钮，仅隐藏模型胶囊避免按钮被整块样式误隐藏

## Validation

- Backend upload API smoke test: passed
- Lowercase omni model request check: passed
- Frontend production build: passed

## Versioning

- root package version: `14.0.0`
- frontend package version: `14.0.0`
- info panel version text: `V14.0`
- git release target: `V14.0`