# Release 10.0

Date: 2026-04-08

Tag: `V10`

一句话版本说明：完成时间感知问候、多轮上下文记忆、前端信息面板与输入体验修复，并记录移动微信端输入法抖动问题，作为后续持续优化项。

## Scope

- request time aware greeting
- rolling context with recent turns and incremental summary
- frontend info entry and debug visibility refinement
- mobile welcome composer fit and desktop auto focus
- known issue logging for mobile WeChat keyboard jitter

## Highlights

1. 后端会话上下文能力升级
- 新增请求时间与时段上下文，避免早晚问候错位。
- 新增基于 `session_id` 的 recent turns 记忆。
- 新增增量式 summary 链路，默认由 `qwen-turbo` 承担低成本上下文压缩。

2. 前端调试与交互体验升级
- 浏览器 Console 可查看精简后的上下文摘要，以及 recent/summary 预览。
- 新增项目信息入口与弹层。
- PC 端完成一轮回复后自动聚焦输入框。
- 移动端/微信端欢迎页输入框宽度与按钮占位重新收紧，避免右侧内容被吃掉。

3. 已记录问题
- 移动微信端输入法抖动问题已纳入版本日志。
- 现象：欢迎页与聊天页在微信 WebView 中，键盘弹起/收起时可能出现头像、标题或输入区轻微位移与抖动。
- 当前状态：已做多轮 CSS 与 viewport 收敛优化，但不同微信内核和设备组合下仍需持续观察。
- 后续方向：继续围绕 visualViewport、safe-area、welcome/chat 双态布局切换做收敛。

## Validation

- Frontend diagnostics: no new errors
- Frontend build: passed (`npm run build`)
- Local backend/frontend restart: passed
- Context logging and recent-turn reuse: verified locally

## Versioning

- root package version: `10.0.0`
- frontend package version: `10.0.0`
- info panel version text: `V10`
- git release target: `V10`