# Release 5.1

Date: 2026-03-26

建议 tag: v5.1.0

一句话 tag: 微信端已完成初步开发并进入移动端收敛阶段。

## Scope
- WeChat webview chat-mode layout and viewport adaptation (initial)
- Message output area expansion and composer spacing tuning
- WeChat-specific interaction stabilization

## Main Changes
- Implemented initial WeChat-targeted frontend layout strategy
- Expanded chat output region in WeChat chat mode to improve readable area
- Reduced excessive spacing between chat output and input composer
- Removed nested assistant bubble scrolling in WeChat mode, unified scrolling at thread level

## Next TODO
1. 移动浏览器端适配（Safari/Chrome/微信外置浏览器）
2. 后端调试 llm_provider：服务启动正常，但单独运行链路疑似中断，需要定位
3. 扩充阿里 Turbo 模型支持（模型清单、选择与回退策略）
4. 各端前端细节修复（样式、交互、键盘与安全区边界）
