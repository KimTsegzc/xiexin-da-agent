# Release 15.0

Date: 2026-04-13

Tag: `V15.0`

一句话版本说明：统一收口邮件技能确认发送链路、全局时间 system 贴尾、职能查询响应口径和身份 Prompt，作为 V15 正式发布。

## Scope

- 邮件技能支持多人收件人，联系人姓名与邮箱可混合输入，真正发送前新增收件人二次确认
- 邮件 SMTP 发送层统一追加 AI agent 尾注，成功出口继续保持原有“邮件已发送”反馈
- 路由器在邮件确认待处理期间强制回到 `send_email`，避免用户回复“是/否”被误判为闲聊
- LLM 调用统一在 system 层补入“今天日期 + 当前时间”，覆盖直接对话与技能自组 messages 两条链路
- 职能查询链路补强负责人链条渲染、领导岗提示、未命中回复与路由口径，并补齐回归测试
- Prompt 身份设定与联系人目录同步更新，统一广州分行身份口径与邮件联系人映射

## Validation

- Python email regression tests: passed
- Python CCB handler regression tests: passed
- Python llm provider regression tests: passed
- Frontend production build: passed
- CI/CD trigger mode: push to `main`

## Versioning

- root package version: `15.0.0`
- frontend package version: `15.0.0`
- info panel version text: `V15.0`
- git release target: `V15.0`