# Release 12.1

Date: 2026-04-09

Tag: `V12.1`

一句话版本说明：去掉微信分享失败提示文案，保留直接生成图片保存流程，并同步升级前端版本信息。

## Scope

- 移除 info 面板中的微信分享失败提示文案
- 保留并优化分享海报预生成与直接保存图流程
- 同步更新前后端版本元数据与前端版本内容到 `V12.1`

## Highlights

1. 分享提示收口
- 去掉“当前环境未直接调起微信分享，已生成图片提示可保存”提示块。
- 点击“转”时直接进入分享图片面板，避免在微信内额外露出环境适配提示。

2. 分享流程保持轻量
- 继续保留分享图预生成逻辑，减少点击“转”时的等待感。
- 海报保存路径不变，继续面向微信端分享失败后的图片保存兜底场景。

## Validation

- Frontend build: passed
- Python compile check: passed

## Versioning

- root package version: `12.1.0`
- frontend package version: `12.1.0`
- info panel version text: `V12.1`
- git release target: `V12.1`