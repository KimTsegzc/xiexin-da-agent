# Launcher 说明

这个目录负责项目的本地启动、停止和打包，当前前端链路已经切到 `Taro H5`，后端接口由 `orchestrator.py` 单独提供。

## 文件关系

- `Go_XIEXin.py`
  - 启动核心。
  - 负责检查 Python 和 npm、清理旧进程、启动 `orchestrator.py --serve`、启动 Taro H5 前端、等待前后端就绪、打开浏览器。
  - `Go_XIEXin.exe` 本质上就是它打包后的结果。

- `start_frontend_silent.ps1`
  - 启动包装脚本。
  - 默认直接调用 Python 执行 `Go_XIEXin.py`，避免命中旧版 exe 残留。
  - 如果显式传入 `-UseLauncherExe`，才会调用根目录下的 `Go_XIEXin.exe`。
  - 如果显式传入 `-PythonOverride`，则强制使用指定 Python 执行 `Go_XIEXin.py`。
  - `-WeChat` 仅保留为兼容参数，不再改变启动入口。

- `stop_frontend.ps1`
  - 停止包装脚本。
  - 默认直接调用 Python 版启动器的 `--stop`。
  - 如果显式传入 `-UseLauncherExe`，才会调用 exe 的 `--stop`。
  - 如果显式传入 `-PythonOverride`，则使用指定 Python 调用启动器的 `--stop`。
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

`start_frontend_silent.ps1` -> `Go_XIEXin.py` -> `orchestrator.py --serve` + `Gateway/Front/taro-mobile`

兼容参数：

- `--wechat`
- `start_frontend_silent.ps1 -WeChat`

它们现在只用于兼容旧调用方式，不再切换到单独前端入口。

优先级规则：

`传入 -PythonOverride` -> 强制走指定 Python + `Go_XIEXin.py`

`传入 -UseLauncherExe` 且未传入 -PythonOverride 且 `Go_XIEXin.exe` 存在 -> 走 `Go_XIEXin.exe`

`默认情况` -> 走 `Go_XIEXin.py`

日常停止链路：

`stop_frontend.ps1` -> `Go_XIEXin.py --stop`

打包链路：

`build_go_xiexin.ps1` -> PyInstaller -> `Go_XIEXin.exe`

## 一句话理解

`Go_XIEXin.py` 是源头，两个 ps1 是薄包装；它现在会同时拉起 Python 后端和 Taro H5 前端，运行期文件落在仓库根目录的 `.runtime/`，`Go_XIEXin.exe` 是其打包产物。