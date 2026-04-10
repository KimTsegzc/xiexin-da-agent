# Release 13.5

Date: 2026-04-11

Tag: `V13.5`

一句话版本说明：邮件技能补齐联系人查转链路与错误兜底，前端等待态文案和加载交互进一步统一。

## Scope

- 邮件技能新增联系人目录 `contact/contacts.json`，支持人名转邮箱
- 联系人查转算法支持精确命中、文本命中和轻量模糊匹配
- LLM补参后增加二次联系人查转，避免中文收件人直入SMTP
- 邮件发送层增加收件人格式校验与编码异常兜底
- 前端等待态文案统一为连接中/路由中/技能运行中，并保持首个流式输出后立即停止打圈

## Validation

- Backend diagnostics: passed
- Frontend diagnostics: passed
- Local end-to-end checks: passed

## Versioning

- root package version: `13.5.0`
- frontend package version: `13.5.0`
- info panel version text: `V13.5`
- git release target: `V13.5`
