# Gateway Front README

本文件说明 `Gateway/Front` 的前端实现与运行方式，重点覆盖：
- 前后端架构
- 页面基础布局（欢迎态/聊天态）
- 不同端（桌面、移动默认、微信）的逻辑分流
- 输入法弹起（软键盘）导致页面抖动/错位问题的控制方案

## 1. 目录与职责

```text
Gateway/Front/
├─ frontend-core/                     # Web / Taro 共享协议、常量与消息结构
├─ taro-mobile/                       # 当前主前端（Taro + React）
│  ├─ src/pages/chat/index.jsx        # 当前主链路：欢迎态 / 会话页 / 输入区
│  └─ config/index.js                 # Taro 构建配置
└─ reference/                         # 设计/参考素材
```

## 2. 运行架构（Front 在系统中的位置）

前端现在收敛成一条主线：

1. `taro-mobile` 作为当前唯一前端入口
2. `frontend-core` 承担共享协议层，保留协议、常量、消息结构等可复用能力
3. H5 只用于开发热更和浏览器调试，真正要验证软键盘容器能力时应优先跑容器目标

前端并不是单独项目，它和后端 `orchestrator.py` 配套运行：

1. 启动器 `Launcher/Go_XIEXin.py` 启动后端服务（默认 `8765`）
2. 同时启动 `Gateway/Front/taro-mobile`（Taro H5，默认 `8501`）
3. 前端通过 HTTP 调后端接口：
- `GET /api/frontend-config`：获取模型列表与默认模型
- `POST /api/chat/stream`：NDJSON 流式输出
- `POST /api/chat`：非流式兜底

关键实现位置：
- 后端接口定义：`orchestrator.py`
- 模型列表/默认模型来源：`Gateway/Back/settings.py` + `Gateway/Back/llm_provider.py`
- 当前前端接口调用：`Gateway/Front/taro-mobile/src/pages/chat/index.jsx`
- 共享协议层：`Gateway/Front/frontend-core/*.js`
- Taro 移动端入口：`Gateway/Front/taro-mobile/src/pages/chat/index.jsx`

## 2.1 当前迁移策略

当前策略已经调整为主线收敛：

1. 旧 Web 前端已退出主启动链，不再作为默认前端
2. `taro-mobile` 接管当前开发与后续容器化演进
3. Taro H5 只承担开发热更与浏览器调试，不把它等同于“系统容器层”
4. 真正验证软键盘容器能力时，应优先跑 `weapp` 或后续原生容器目标
5. 当前 Taro 首版仍使用 `/api/chat` 非流式接口保证稳定，后续再按端能力补流式

## 2.2 Taro 移动端运行方式

移动端容器端目录：`Gateway/Front/taro-mobile`

首次安装依赖：

```powershell
cd Gateway/Front/taro-mobile
npm install
```

开发命令：

```powershell
npm run dev:h5
npm run dev:weapp
```

一句话判断：

- `dev:h5` = 开发热更，用来快速调 UI 和接口
- `build:*` = 产物打包，不用来日常调试
- 如果你观察的是“手机浏览器仍然顶飞”，那是浏览器路径问题，不是系统容器能力已经生效

如需显式指定后端地址，可在启动前设置环境变量：

```powershell
$env:TARO_APP_API_BASE = "http://127.0.0.1:8765"
```

当前 Taro 首版特性：

1. 欢迎态 / 聊天态 / 输入区主链路已迁入容器端
2. 会话结构、配置协议、消息对象复用 `frontend-core`
3. 输入区底部位移由 `Taro.onKeyboardHeightChange` 驱动
4. assistant 回复已支持基础 markdown 富文本渲染

## 3. 页面基础布局

现在前端不再把所有逻辑堆在一个组件里，而是按“调度器 + 壳层 + 共享组件”组织。页面核心仍然是两态切换：

1. 欢迎态（`welcome-mode`）
- 中央头像 + 打字式标题文案
- 底部输入气泡（模型标签、输入框、发送按钮）
- 进入第一轮提问后切到聊天态

2. 聊天态（`chat-mode`）
- 消息线程区（用户气泡 + assistant 渲染 markdown）
- 输入气泡固定在底部
- 设置按钮（MODEL）支持弹层切换模型
- 桌面大屏存在左侧 rail 区，移动端收敛为顶部区域

头像交互：
- 所有 avatar 都接入点击播放视频
- 使用“底图常驻 + 视频叠层淡入淡出 + 延迟 reset”避免首尾闪白

## 4. 容器问题判断

当前要明确区分两件事：

1. `Taro H5` 仍然是浏览器目标，只适合开发热更和浏览器调试
2. `Taro weapp` 或后续原生容器目标，才是“系统容器层”真正生效的路径

所以如果你现在在手机浏览器里看到“输入法顶飞”，这只能说明浏览器路径的问题还在，不代表容器方案无效。

## 5. 当前输入法策略

当前 Taro 主链路里，输入区底部位移由 `Taro.onKeyboardHeightChange` 驱动，核心代码在 `taro-mobile/src/pages/chat/index.jsx`：

1. 欢迎态和聊天态已经都归到同一个页面容器
2. 输入区通过 `keyboardHeight` 做底部补偿
3. 消息线程和输入区不再依赖旧 Web 的 `visualViewport + scrollTo` 补偿链

这意味着：

1. 浏览器 H5 调试时，只能验证页面结构、接口链路和基础样式
2. 真正要验证“是否还顶飞”，必须进 `dev:weapp` 或后续原生容器实机

## 6. 接口与渲染说明

前端提交：

```json
POST /api/chat/stream
{
  "user_input": "...",
  "smooth": true,
  "model": "qwen-turbo"
}
```

后端返回 NDJSON 事件：
- `pulse`：accepted / first_token
- `delta`：流式分片
- `done`：最终文本和 metrics
- `error`：错误事件

当前首版 Taro 页面先走 `/api/chat` 非流式请求，保证容器链路先稳定。

新增能力：
- 会话消息会写入 `localStorage`，默认保留最近一段历史，移动端刷新后不会直接丢失上下文
- 配置获取、消息结构、markdown 渲染都已下沉到 `frontend-core`，后续不要再把逻辑拆回旧 Web 项目

## 7. 本地开发

在 `Gateway/Front/taro-mobile`：

```bash
npm install
npm run dev:h5
npm run dev:weapp
```

H5 开发入口：
- `http://127.0.0.1:8501/`

注意：`dev:h5` 用来热更调试，不用来判断“系统容器层是否已经解决键盘顶飞”。

完整联调推荐通过 Launcher 启动（同时拉起 backend + frontend）：
- `Launcher/start_frontend_silent.ps1`
- 或 `Launcher/Go_XIEXin.py`

## 8. 常见排查

1. 模型列表空
- 检查 `GET /api/frontend-config` 是否可达
- 检查后端 `.env` 与 `Gateway/Back/settings.py`

2. 流式不动
- 检查 `POST /api/chat/stream`
- 看 `.runtime/backend-8765*.log`

3. 移动端键盘导致错位
- 如果是 H5 浏览器：这是浏览器路径问题，先不要把它误判成“容器层失败”
- 如果是小程序或容器端：检查 `Taro.onKeyboardHeightChange` 是否有事件回调
- 看输入区底部 padding 是否跟随 `keyboardHeight` 变化

---

维护建议：
- 后续所有移动端改动，优先继续收敛在 `taro-mobile` 和 `frontend-core`
- 不要再恢复旧 Web 前端作为主入口
- 浏览器调试和容器验证要分开看，不要混在同一结论里