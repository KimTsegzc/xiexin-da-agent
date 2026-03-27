# Release 7.0

Date: 2026-03-27

建议 tag: v7.0.0

一句话 tag: 前端架构正式切到 Taro + React + Vant，整体工程开始对齐 FastAPI 目标形态。

## Scope
- Frontend architecture migration to Taro workspace
- React Vant mobile UI baseline setup
- Front/back project structure refresh for the next FastAPI phase

## Main Changes
- 前端主工作区切换为 `Gateway/Front`，由 `package.json + scripts + taro-mobile` 组织多端构建入口
- 原 `react-ui` 方案退出主路径，当前前端以 Taro + React + Vant 为新的迭代基线
- 抽出 `frontend-core` 作为前端协议与基础能力承载层，便于后续继续做多端复用
- 启动与说明文档同步调整，当前仓库结构已开始为后续 FastAPI 化改造预留空间

## Known Status
- 前端架构升级已完成封板，可作为 V7.0 基线继续推进
- 后端目前仍未完成 FastAPI 改造，本次版本更多体现为架构切换与轨道切换

## Versioning
- Root project version bumped to 7.0.0
- Front workspace version bumped to 7.0.0
- Taro mobile package version bumped to 7.0.0

## Next TODO
1. 在 Vant 体系下继续优化前端交互与视觉，需要重新做一轮设计
2. 后端从现有实现迁移到 FastAPI，完成接口层与运行方式改造