# Gateway Front README

本文件说明 `Gateway/Front` 的前端实现与运行方式，重点覆盖：
- 前后端架构
- 页面基础布局（欢迎态/聊天态）
- 不同端（桌面、移动默认、微信）的逻辑分流
- 输入法弹起（软键盘）导致页面抖动/错位问题的控制方案

## 1. 目录与职责

```text
Gateway/Front/
├─ react-ui/                 # React + Vite 主前端
│  ├─ src/
│  │  ├─ App.jsx             # 主要页面逻辑（状态、交互、接口、端逻辑）
│  │  ├─ styles.css          # 全量布局与多端样式策略
│  │  └─ main.jsx            # React 入口
│  ├─ public/                # 静态资源（头像、交互视频等）
│  ├─ wechat/index.html      # 微信入口（注入 __APP_CLIENT_MODE=wechat）
│  ├─ index.html             # 默认入口
│  └─ vite.config.js         # 双入口构建（main + wechat）
└─ reference/                # 设计/参考素材
```

## 2. 运行架构（Front 在系统中的位置）

前端并不是单独项目，它和后端 `orchestrator.py` 配套运行：

1. 启动器 `Launcher/Go_XIEXin.py` 启动后端服务（默认 `8765`）
2. 同时启动 `Gateway/Front/react-ui`（Vite，默认 `8501`）
3. 前端通过 HTTP 调后端接口：
- `GET /api/frontend-config`：获取模型列表与默认模型
- `POST /api/chat/stream`：NDJSON 流式输出
- `POST /api/chat`：非流式兜底

关键实现位置：
- 后端接口定义：`orchestrator.py`
- 模型列表/默认模型来源：`Gateway/Back/settings.py` + `Gateway/Back/llm_provider.py`
- 前端接口调用：`Gateway/Front/react-ui/src/App.jsx`

## 3. 页面基础布局

`App.jsx` 的核心是两态切换：

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

## 4. 几个端的逻辑（模式分流）

前端模式判定在 `App.jsx`：

1. 微信强制入口
- `react-ui/wechat/index.html` 注入：`window.__APP_CLIENT_MODE = "wechat"`

2. URL 强制
- `?client=wechat` 或 `?mode=wechat`

3. UA 自动识别
- `micromessenger` 或 `window.__wxjs_environment === "miniprogram"`

4. 默认模式（default）下的移动端对齐
- 运行时根据 `window.innerWidth <= 900` 识别移动端
- 默认移动端会追加 `is-mobile-default`，并复用微信端移动布局与字号 token

结果：
- 桌面 default：桌面布局
- 微信：`is-wechat` 路径
- 非微信但移动端：`is-mobile-default`，行为与微信端对齐（含键盘处理策略）

## 5. 输入法弹起问题：控制机制详解

这是当前前端最关键的一块。

### 5.1 问题本质

在移动端 WebView（尤其微信）中，软键盘弹起会改变可视 viewport，常见副作用：
- 固定元素漂移
- 页面整体被顶起
- 滚动位置错乱
- 输入框/按钮抖动

### 5.2 当前方案（代码级）

#### A. 维护动态 viewport 变量

在 `App.jsx` 中监听：
- `window.resize`
- `visualViewport.resize`
- `visualViewport.scroll`

并持续写入 CSS 变量：
- `--app-height`
- `--app-height-stable`
- `--app-width`
- `--app-width-stable`
- `--keyboard-offset`

其中：
- `--app-height`：当前可视高度
- `--app-height-stable`：稳定最大高度（防止来回抖）
- `--keyboard-offset`：键盘抬升量

#### B. 欢迎态锁定条件

`welcomeLockActive` 条件：
- 移动端微信路径（`is-wechat`）或移动端默认路径（`is-mobile-default`）
- 且当前是欢迎态（`!chatMode`）

激活后：
- 给 `html/body` 打 `data-welcome-lock="true"`
- CSS 设置 `overflow: hidden; overscroll-behavior: none;`

#### C. 欢迎态固定栈锁底

欢迎态下 `.welcome-stack-shell` 使用绝对定位，`bottom` 由：
- `--wechat-welcome-lock-bottom`

该值由 JS 根据键盘偏移与稳定高度计算，避免键盘弹起时主视觉和输入框乱跳。

#### D. 强制回滚页面滚动

欢迎态锁定时会监听 `scroll` + `visualViewport.scroll`，并通过 `window.scrollTo(0, 0)` 维持页面不被拖偏。

#### E. 禁止移动欢迎态自动聚焦

`allowWelcomeAutoFocus` 在移动端路径为 `false`，避免首屏一加载就触发键盘导致布局突变。

### 5.3 修改这块时的硬性注意

1. 不要移除欢迎态的固定容器结构：
- `.app-shell.is-wechat.welcome-mode`
- `.app-shell.is-mobile-default.welcome-mode`
- `.welcome-stack-shell`

2. 不要删除 viewport/keyboard 变量写入逻辑。

3. 不要把移动欢迎态 `autoFocus` 改回 `true`。

4. 修改输入区高度/字号时，优先改 token，不要直接破坏 `--chat-composer-height`、`--composer-bottom`、`--thread-surface-offset` 的关系。

## 6. 样式系统与多端统一策略

`styles.css` 使用三层策略：

1. 全局默认（桌面优先）
2. `@media (max-width: 900px)` 移动端覆写
3. 模式 class 细分：
- `is-wechat`
- `is-mobile-default`
- `chat-mode` / `welcome-mode`

目前“移动默认端”和“微信端”已经统一到同一组字号 token（在 `.app-shell.is-wechat, .app-shell.is-mobile-default` 下），后续调字号只改一处。

## 7. 接口与流式渲染说明

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

前端在 `App.jsx` 中按事件实时拼接 assistant 内容，并展示首 token 和总耗时。

## 8. 本地开发

在 `Gateway/Front/react-ui`：

```bash
npm install
npm run dev
```

默认端入口：
- `http://127.0.0.1:8501/`

微信入口：
- `http://127.0.0.1:8501/wechat/`

完整联调推荐通过 Launcher 启动（同时拉起 backend + frontend）：
- `Launcher/start_frontend_silent.ps1`
- 或 `Launcher/Go_XIEXin.py`

## 9. 常见排查

1. 模型列表空
- 检查 `GET /api/frontend-config` 是否可达
- 检查后端 `.env` 与 `Gateway/Back/settings.py`

2. 流式不动
- 检查 `POST /api/chat/stream`
- 看 `.runtime/backend-8765*.log`

3. 移动端键盘导致错位
- 先确认是否进入 `welcomeLockActive`
- 检查 `data-welcome-lock` 是否正确挂到 `html/body`
- 检查 `--keyboard-offset` 与 `--wechat-welcome-lock-bottom` 是否在变化

---

维护建议：后续所有“移动端体验”改动，优先在 `is-wechat` 与 `is-mobile-default` 共用层改 token；只有明确需要差异化时，再拆分独立规则。