# Release 15.1

Date: 2026-04-13

Tag: `V15.1`

一句话版本说明：收口欢迎语为固定默认文案、补强职能查询负责人脱敏，并把 CI/CD 扩到后端回归测试和版本 tag 触发发布。

## Scope

- 欢迎语链路新增 `XIEXIN_WELCOME_FIXED_DEFAULT` 开关，默认固定展示“你好~我是广分谢鑫😀”
- `frontend-config` debug payload 同步输出欢迎语实际模式，便于区分固定默认与本地 sayings 随机模式
- 职能查询数据加载、模型上下文和链条渲染统一对负责人姓名做脱敏
- CCB handler 回归测试同步更新，覆盖负责人脱敏与链条渲染输出
- GitHub Actions `CI Gate` 新增后端回归测试
- GitHub Actions `CD Deploy` 在部署前执行后端回归测试和前端构建校验
- GitHub Actions 支持 `V*` tag 触发，支持 `V15.1` push 后直接发版部署

## Validation

- Python unit tests: passed
- Frontend production build: passed
- CI gate: updated to run backend regression tests and frontend build
- CD deploy: updated to validate backend tests and frontend build before SSH deploy
- Release trigger mode: push to `main` or tag `V15.1`

## Versioning

- root package version: `15.1.0`
- frontend package version: `15.1.0`
- git release target: `V15.1`