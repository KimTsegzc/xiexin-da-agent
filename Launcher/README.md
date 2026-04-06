# Launcher 说明

这个目录负责项目本地联调与打包，默认走“前后一体”全栈启动：

- 后端：`apps.api.server --serve`（由 `Go_XIEXin.py` 拉起）
- 前端：`Front/react-ui`（Vite dev server）

## 主文件

- `Go_XIEXin.py`
  - 启动核心。
  - 检查 Python 与 npm、清理旧进程、启动后端模块与前端、等待健康检查通过、可选打开浏览器。
  - `Go_XIEXin.exe` 是它的打包产物。

- `start_stack.ps1`
  - 全栈启动包装脚本（前后一体）。
  - 默认走 Python 脚本模式；传 `-UseLauncherExe` 可走 exe。

- `stop_stack.ps1`
  - 全栈停止包装脚本（前后一体）。
  - 停止前端端口与后端端口对应进程。

- `restart_stack.ps1`
  - 全栈重启包装脚本。
  - 顺序执行 stop -> wait -> start，避免竞态。

- `build_go_xiexin.ps1`
  - 使用 PyInstaller 打包 `Go_XIEXin.py` 为根目录 `Go_XIEXin.exe`。

- `Go_XIEXin.ico`
  - 启动器图标资源。

## 日常命令

- 启动：`powershell -ExecutionPolicy Bypass -File Launcher/start_stack.ps1 -Port 8501`
- 停止：`powershell -ExecutionPolicy Bypass -File Launcher/stop_stack.ps1 -Port 8501`
- 重启：`powershell -ExecutionPolicy Bypass -File Launcher/restart_stack.ps1 -Port 8501`

可选参数：

- `-NoBrowser`：启动后不自动打开浏览器
- `-PythonOverride <path>`：指定 Python 解释器
- `-UseLauncherExe`：使用 `Go_XIEXin.exe` 路径
- `-WeChat`：兼容参数，保留但不切换单独入口

## 一句话

`Go_XIEXin.py` 是源头，`start/stop/restart_stack.ps1` 是统一薄包装，运行期文件在仓库根 `.runtime/`。