# AI 开发日志 - 2026-03-25

## 2.0 当前完成（后端）
1. 已完成 `orchestrator -> Gateway.Back.llm_provider` 的主链路打通，后端可直接以流式方式输出模型响应。
2. 已统一事件协议为 `pulse / delta / done / error`，并补充 `first_token_latency_seconds`、总耗时、模型名等指标。
3. 已完成 provider 命名与导入规范化，当前可以直接 `from Gateway.Back import LLMProvider`。
4. `orchestrator.py` 已承担统一入口与流式编排职责，并提供轻量 HTTP 流接口给前端调用。
5. `config.json` 已整理为带说明字段的结构，运行参数放在 `llm_provider_config` 下。
6. provider 快速说明文档已同步到当前实现。

## 2.0 当前完成（前端）
1. `Gateway/Front/app.py` 已壳化，改为 Streamlit 宿主，只负责加载独立的 HTML / CSS / JS。
2. 已保留 `app_v1_0.py` 作为前端 1.0 快照，便于回看与回退。
3. 聊天页结构已拆分到 `Gateway/Front/ui/index.html`、`styles.css`、`app.js`。
4. 前端已接通 orchestrator 的流式接口，能实时消费 `pulse / delta / done / error` 并渲染聊天消息。
5. 首次提问后，页面可从欢迎态切换到聊天态，输入框、头像、消息区会重排到对话布局。

## 目前存在的问题
1. Streamlit 壳 + `components.html` iframe 的双层高度系统，导致全屏、100% 缩放、浏览器提示条等场景下，聊天页天地脚难以稳定到产品级精度。
2. Streamlit 启动环境存在不一致风险，曾出现系统 Python 进程占用 8501，而不是项目 `.venv311` 进程提供页面的情况。
3. 当前工作区较脏，`.venv311` 和若干素材文件容易出现在发布候选里，增加误提交风险。
4. 前端 UI 已可用，但仍属于“可演示”状态，尚未形成稳定的最终布局规则。
5. skill 体系还停留在架构建议阶段，尚未落地统一 skill 契约与示例实现。

## 分析与建议
1. `orchestrator.py` 应继续保持编排层定位，只负责入口、路由、事件整形，不要把 skill 细节塞进去。
2. 保留 Streamlit 作为当前宿主是务实选择，适合继续推进后端能力和产品验证，但前端布局不宜再追求像素级极限打磨。
3. 前后端应继续坚持统一事件契约，前端只消费标准事件，不感知 provider 细节，这一点已经是当前架构的正确方向。
4. 后续如果 UI 要进入正式产品化阶段，建议把前端独立出去；如果仍以快速试验为主，当前 Streamlit 壳方案可以继续保留。
5. 发布流程应严格白名单 staging，显式排除 `.venv311`、缓存目录和无关素材。

## 下一步建议
1. 定一版最小 skill 契约文档，先约束输入、输出、错误结构。
2. 增加最小 smoke check：验证 `accepted -> first_token -> done` 顺序与 metrics 完整性。
3. 前端如果继续保留 Streamlit，建议把重点转向可用性与稳定性，不再耗费过多时间在壳层天地脚微调上。

## 2.1 当前整体进度
1. 前端消息区已补上基础 Markdown 渲染，当前支持标题、段落、列表、引用、链接、行内代码和代码块。
2. 前端助手消息已从纯 `textContent` 渲染切换为结构化消息内容渲染，等待态与错误态仍保持纯文本显示。
3. 已补充 Windows 静默启动脚本，当前可通过 `Launcher/start_frontend_silent.ps1` 和 `stop_frontend.ps1` 无黑框启动或停止前端。
4. 已修正静默启动脚本的项目根目录解析与隐藏窗口启动方式，当前可同时拉起 8501 前端端口和 8765 orchestrator 流接口。
5. 仓库内旧命名文件 `LLM-provider.py`、`LLM-provider-function.md` 已进入清理收尾阶段，主实现与文档以 `llm_provider.py`、`llm-provider_function.md` 为准。

## 相比 2.0.1 的主要改动
1. 前端新增基础 Markdown 渲染能力，模型输出的结构化内容不再以纯文本形式展示。
2. 前端样式已补充 Markdown 相关展示规则，包括代码块、引用、列表和内联代码。
3. 新增静默启动与停止脚本，解决“启动必须看到黑框”的使用问题。
4. 启动链路已验证可在静默模式下同时带起 Streamlit 前端与 orchestrator 内部流服务。
5. 发布忽略规则已补充 `.venv311` 与 `.streamlit` 前端运行产物，降低后续误提交风险。
