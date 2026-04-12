# Release 14.3.1

Date: 2026-04-12

Tag: `V14.3.1`

一句话版本说明：修复开屏欢迎语从 sayings 选词时 recent-10 去重失真，兼容历史缓存与新 emoji 文案混用场景。

## Scope

- 欢迎语比较改为基于规范化 quote key，避免旧缓存无 emoji 与新 sayings 带 emoji 被误判为不同文案
- welcome history 恢复为真实最近 10 次展示序列，而不是去重后的唯一集合
- 新增欢迎语回归测试，覆盖 legacy cache 与 recent sequence 两个关键场景

## Validation

- Python welcome regression tests: passed
- Frontend production build: passed
- CI/CD trigger mode: push to `main`

## Versioning

- root package version: `14.3.1`
- frontend package version: `14.3.1`
- info panel version text: `V14.3.1`
- git release target: `V14.3.1`