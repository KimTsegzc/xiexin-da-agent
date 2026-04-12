# Release 14.3

Date: 2026-04-12

Tag: `V14.3`

一句话版本说明：多模态上传能力临时收口为仅支持图片解析，前端在选择与提交阶段都对非图片文件进行明确拦截。

## Scope

- 上传控件增加 `image/*` 限制，只允许选择图片文件
- 前端附件处理阶段过滤非图片文件，并提示“暂时只支持图片解析”
- 请求层新增图片类型兜底，避免 `txt/pdf` 再进入上传链路
- 保留前序修复：上传 413 提示、nginx 上传大小限制、omni 模型名小写修正

## Validation

- Frontend production build: passed
- Local image-only upload guard: passed
- CI/CD trigger mode: push to `main`

## Versioning

- root package version: `14.3.0`
- frontend package version: `14.3.0`
- info panel version text: `V14.3`
- git release target: `V14.3`