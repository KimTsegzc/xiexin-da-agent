---
name: skill-send-email
description: 'Use when the user explicitly asks to send an email and provides or can provide receiver, subject, and body.'
---

# Send Email Skill

## Purpose
将前端明确的“发送邮件”指令转换为后端 SMTP 发送动作。

## Use When
- 用户明确要求发送邮件、代发邮件、通知邮件。
- 用户在输入中提供了收件人、主题、正文，或可通过追问补齐这些字段。

## Avoid When
- 纯闲聊、开放问答、寒暄类请求。
- 分行内部岗位职责与办公号码查询类请求。

## Input Contract
优先读取 `AgentRequest.metadata.email`：
- `receiver`
- `subject`
- `body`

兼容从 `user_input` 提取：
- JSON 负载：发送邮件 {"receiver":"a@b.com","subject":"测试","body":"你好"}
- 键值文本：发送邮件 主题:测试 正文:你好 收件人:a@b.com

## Output Contract
- 成功：返回“邮件已发送”并带收件人、主题、传输通道。
- 失败：返回失败原因，便于前端展示或重试。
- 参数缺失：返回规范化使用提示，指导前端补齐字段。

## Runtime Notes
- 实际发送能力通过 `Backend.integrations.email_sender` 执行。
- 遵循 SMTP 配置开关，未启用时返回明确错误。
- 支持联系人查转：优先从 `data/contacts.json` 将人名/别名转换为邮箱地址。
- 查转策略：精确匹配 > 文本命中 > 轻量模糊匹配（用于小范围错别字兜底）。
