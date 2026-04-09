# Release 12.0

Date: 2026-04-09

Tag: `V12.0`

一句话版本说明：完成 Info 面板互动能力与移动端样式收口，并将转发图片重构为正式分享海报。

## Scope

- info 面板新增点赞、转发、评论互动能力
- 微信端 / 移动端 info 样式与滚动体验统一优化
- 转发海报改版，二维码区与排版适配分享场景
- 版本文案与发布元数据同步升级到 `V12.0`

## Highlights

1. Info 互动能力上线
- 新增点赞、转发、评论三类操作入口。
- 赞评数据接入后端持久化接口，支持会话态识别。

2. 移动端体验收口
- 微信端与默认移动端的 info 弹层间距、排版、按钮尺寸与评论区样式统一优化。
- 操作按钮、评论输入与滚动区域针对移动端做了细节收敛。

3. 分享海报重做
- 转发图片改为正式海报风格，支持更清晰的标题、说明信息与二维码展示。
- 分享图支持预生成，点击“转”时减少现场生成等待。

## Validation

- Frontend build: passed
- Share poster generation: passed in local build flow
- Version metadata sync: passed

## Versioning

- root package version: `12.0.0`
- frontend package version: `12.0.0`
- info panel version text: `V12.0`
- git release target: `V12.0`