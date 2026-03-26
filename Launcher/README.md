# Launcher 说明

这个目录负责项目的本地启动、停止和打包，关系如下。

## 文件关系

- `Go_XIEXin.py`
  - 启动核心。
  - 负责检查 Python、清理旧进程、启动 Streamlit、等待前端就绪、打开浏览器。
  - `Go_XIEXin.exe` 本质上就是它打包后的结果。

- `start_frontend_silent.ps1`
  - 启动包装脚本。
  - 默认优先调用根目录下的 `Go_XIEXin.exe`。
  - 如果显式传入 `-PythonOverride`，则强制改走 Python 执行 `Go_XIEXin.py`。
  - 如果 exe 不存在，也会回退到 Python 执行 `Go_XIEXin.py`。

- `stop_frontend.ps1`
  - 停止包装脚本。
  - 默认优先调用 exe 的 `--stop`。
  - 如果显式传入 `-PythonOverride`，则强制改走 Python 版启动器的 `--stop`。
  - 调用 exe 或 Python 版启动器的 `--stop` 模式，关闭当前前端进程。

- `build_go_xiexin.ps1`
  - 打包脚本。
  - 使用 PyInstaller 把 `Go_XIEXin.py` 打成根目录下的 `Go_XIEXin.exe`。
  - 使用 `Launcher/Go_XIEXin.ico` 作为图标来源，并处理 exe 图标资源。

- `Go_XIEXin.ico`
  - 启动器图标资源。
  - 专门给 `build_go_xiexin.ps1` 打包 exe 时使用。

## 运行关系

日常启动链路：

`start_frontend_silent.ps1` -> `Go_XIEXin.exe` 或 `Go_XIEXin.py` -> `Gateway/Front/app.py`

优先级规则：

`传入 -PythonOverride` -> 强制走 `Go_XIEXin.py`

`未传入 -PythonOverride` 且 `Go_XIEXin.exe` 存在 -> 优先走 `Go_XIEXin.exe`

`未传入 -PythonOverride` 且 exe 不存在 -> 回退到 `Go_XIEXin.py`

日常停止链路：

`stop_frontend.ps1` -> `Go_XIEXin.exe --stop` 或 `Go_XIEXin.py --stop`

打包链路：

`build_go_xiexin.ps1` -> PyInstaller -> `Go_XIEXin.exe`

## 一句话理解

`Go_XIEXin.py` 是源头，两个 ps1 是薄包装，`Go_XIEXin.exe` 是打包产物。