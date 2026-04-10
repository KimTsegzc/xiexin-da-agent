# Launcher 说明

这个目录负责项目本地联调与打包，默认走"前后一体"全栈启动：

- 后端：`apps.api.server --serve`（由 `Go_XIEXin.py` 拉起）
- 前端：`Front/react-ui`（Vite dev server）

## 目录结构

```
Launcher/
├── Mac/                  # macOS / Mac Studio 脚本
│   ├── start.sh          # 启动全栈
│   ├── stop.sh           # 停止全栈
│   └── restart.sh        # 重启全栈
├── Win/                  # Windows 脚本
│   ├── start.ps1         # 启动全栈
│   ├── stop.ps1          # 停止全栈
│   ├── restart.ps1       # 重启全栈
│   └── build.ps1         # PyInstaller 打包 Go_XIEXin.exe
├── Ubuntu/               # Ubuntu 线上服务启停脚本（systemd）
│   ├── start.sh          # 启动后端+前端服务
│   ├── stop.sh           # 停止后端+前端服务
│   └── restart.sh        # 重启后端+前端服务
├── Go_XIEXin.py          # 启动核心（跨平台）
├── Go_XIEXin.ico         # 启动器图标（打包用）
└── README.md
```

## Mac 日常命令

```bash
# 启动（自动打开浏览器）
./Launcher/Mac/start.sh

# 不打开浏览器
./Launcher/Mac/start.sh --no-browser

# 停止
./Launcher/Mac/stop.sh

# 重启
./Launcher/Mac/restart.sh
```

可选参数：`--port <n>`（默认 8501）、`--no-browser`

## Windows 日常命令

```powershell
# 启动
powershell -ExecutionPolicy Bypass -File Launcher\Win\start.ps1 -Port 8501

# 停止
powershell -ExecutionPolicy Bypass -File Launcher\Win\stop.ps1 -Port 8501

# 重启
powershell -ExecutionPolicy Bypass -File Launcher\Win\restart.ps1 -Port 8501

# 打包 exe
powershell -ExecutionPolicy Bypass -File Launcher\Win\build.ps1
```

可选参数：`-NoBrowser`、`-PythonOverride <path>`、`-UseLauncherExe`

## Ubuntu 日常命令

```bash
# 启动线上服务（systemd）
bash Launcher/Ubuntu/start.sh

# 停止线上服务
bash Launcher/Ubuntu/stop.sh

# 重启线上服务
bash Launcher/Ubuntu/restart.sh
```

可选环境变量：`APP_DIR`（默认 `/srv/xiexin-da-agent`）、`BACKEND_SERVICE`（默认 `xiexin-backend`）、`FRONTEND_SERVICE`（默认 `xiexin-frontend`）

## 运行时文件

启动后的 pid / log 文件写入仓库根 `.runtime/`，由 stop 脚本清理。

## 一句话

`Go_XIEXin.py` 是跨平台启动核心，`Mac/` 与 `Win/` 是各自平台的薄包装。
