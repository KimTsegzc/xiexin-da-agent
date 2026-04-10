# Release 13.1

Date: 2026-04-11

Tag: `V13.1`

一句话版本说明：补齐 Ubuntu 启停脚本，统一线上运维动作，修复部署后“已配环境但未生效”的排查成本。

## Scope

- 新增 `Launcher/Ubuntu/start.sh`，统一 systemd 启动流程
- 新增 `Launcher/Ubuntu/stop.sh`，统一 systemd 停止流程
- 新增 `Launcher/Ubuntu/restart.sh`，支持一键重启线上服务
- 更新 `Launcher/README.md`，补充 Ubuntu 命令文档
- 同步版本号与前端版本信息到 `V13.1`

## Validation

- Ubuntu service script syntax: passed
- Version metadata consistency: passed

## Versioning

- root package version: `13.1.0`
- frontend package version: `13.1.0`
- info panel version text: `V13.1`
- git release target: `V13.1`
