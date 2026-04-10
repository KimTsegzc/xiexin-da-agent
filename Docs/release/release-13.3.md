# Release 13.3

Date: 2026-04-11

Tag: `V13.3`

一句话版本说明：邮件技能默认改为“搜索优先”，先检索新消息再生成可发送内容。

## Scope

- 扩展 `send_email` skill：默认启用搜索优先增强流程
- 新增关键词和长度判定，自动触发 qwen-turbo + `enable_search=true`
- 在成功/失败 metrics 中增加搜索增强开关与模型信息
- 保留 V13.2 的失败解释能力，与搜索优先逻辑兼容
- 为后续 Memory 缓存检索与附件发送保留扩展点

## Validation

- Python syntax check: passed
- Skill file diagnostics: passed

## Versioning

- root package version: `13.3.0`
- frontend package version: `13.3.0`
- info panel version text: `V13.3`
- git release target: `V13.3`
