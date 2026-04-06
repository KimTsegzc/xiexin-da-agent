# Release 5.3

Date: 2026-03-27

建议 tag: v5.3.0

一句话 tag: 前端移动端与微信端逻辑完成对齐，欢迎态输入法稳定策略文档化并纳入正式发布。

## Scope
- Frontend multi-end behavior alignment (desktop/mobile/wechat)
- Input-method popup stabilization in welcome mode
- Avatar interaction continuity and settings/composer refinement
- Launcher binary and soul profile updates

## Main Changes
- 新增 Front 专项文档：`Gateway/Front/README.md`，完整说明前端架构、页面布局、多端逻辑与输入法弹起控制机制
- React UI 多端策略统一：移动端默认模式与微信端在布局/字号/交互逻辑上对齐
- 欢迎态输入法弹起控制强化：基于 `visualViewport` 与稳定高度变量，结合 welcome lock，避免页面整体抖动/错位
- MODEL 选择文案统一、设置按钮位置与交互修复、聊天/欢迎态输入区尺寸体系收敛
- Avatar 点击视频交互完善：音频恢复、起播与结束闪白修复、播放过渡更连贯
- 包含发布资产更新：`Go_XIEXin.exe`、`soul.md`

## Versioning
- React UI package version bumped to 5.3.0

## Next TODO
1. 真机回归：iOS Safari、安卓 Chrome、微信内置 WebView 的键盘弹起与旋转屏行为
2. 头像视频资源进一步压缩与首帧优化，降低首播延迟
3. 为 Front README 增补时序图（启动链路、流式事件链路、键盘锁定链路）
