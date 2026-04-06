# Release 6.0

Date: 2026-03-27

建议 tag: v6.0.0

一句话 tag: 微信端输入法稳定性大幅收敛，前端完成壳层/运行时拆分并进入移动端非微信浏览器问题收尾阶段。

## Scope
- Frontend architecture split for desktop/mobile/wechat shells
- WeChat keyboard stability hardening in welcome mode and chat mode
- Mobile viewport and composer positioning refactor
- Release asset refresh for frontend avatar resources

## Main Changes
- `App.jsx` 完成瘦身，前端按 `shells / hooks / components / utils` 拆分，桌面端、移动端、微信端的职责边界明确
- 输入法处理从页面级散落逻辑收敛到独立运行时：`useViewportMetrics`、`useAppScrollLock`、`useDismissKeyboardOnThreadScroll`、`useThreadAutoScroll`
- 微信端聊天态已基本稳住：采用稳定高度壳层 + 内部 `keyboard-offset` 位移策略，欢迎态改为完全静止布局
- 新增会话持久化、设置面板组件化、新会话入口、前端 API/base url 解析收敛
- Front README 已补齐当前前端结构与运行机制说明，便于后续继续治理

## Known Status
- 微信端：当前聊天态和欢迎态的输入法抖动问题已明显改善，可作为本次封板版本基线
- 非微信移动端：输入法弹起时顶部元素被顶飞、输入区与输出区错位问题仍然严重，尚未达到封板意义上的“已解决”

## Versioning
- Root project version bumped to 6.0.0
- React UI package version bumped to 6.0.0

## Next TODO
1. 针对 `is-mobile-default` 做真机回归，优先覆盖 Android Chrome / Edge / OEM WebView
2. 继续收敛移动端输入法链路，必要时将聊天态与欢迎态的 keyboard state 彻底解耦
3. 清理历史实验 memo，只保留正式发布与问题跟踪文档