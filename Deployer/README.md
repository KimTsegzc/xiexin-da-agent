# Deployer

Ubuntu 可以用，而且对这个项目是合适的。

当前项目结构更适合这种部署方式：
- Python 后端常驻在 `8766`（仅本机回环）
- React 前端常驻在 `8501`
- 由 `systemd` 托管进程
- 由 `nginx` 对外暴露入口

## 建议环境

- Ubuntu 22.04 LTS 或 24.04 LTS
- Python 3.10+ (recommended 3.11+)
- Node.js 20+
- npm 10+
- nginx
- `git`, `curl`, `python3-venv`

## 本目录内容

- [env.production.example](env.production.example): 生产环境变量模板
- [preflight_ubuntu.sh](preflight_ubuntu.sh): 部署前检查脚本
- [bootstrap_ubuntu.sh](bootstrap_ubuntu.sh): Ubuntu 初始化脚本
- [healthcheck.sh](healthcheck.sh): 部署后健康检查脚本
- [systemd/xiexin-backend.service](systemd/xiexin-backend.service): 后端服务模板
- [systemd/xiexin-frontend.service](systemd/xiexin-frontend.service): 前端服务模板
- [nginx/xiexin-da-agent.conf](nginx/xiexin-da-agent.conf): nginx 配置模板

## 推荐部署路径

假设仓库部署在：
- `/srv/xiexin-da-agent`

建议运行用户：
- `xiexin`

## 快速流程

### 1. 服务器拉代码

```bash
cd /srv
sudo git clone <your-repo-url> xiexin-da-agent
cd /srv/xiexin-da-agent
```

### 2. 执行预检查

```bash
bash Deployer/preflight_ubuntu.sh
```

### 3. 初始化环境

```bash
bash Deployer/bootstrap_ubuntu.sh
```

### 4. 配置环境变量

```bash
cp Deployer/env.production.example .env
nano .env
```

至少要填：
- `ALIYUN_BAILIAN_API_KEY`

## 当前前后端端口设计

生产推荐链路：
- 浏览器仅访问 `80/443`（nginx）
- nginx 反向代理到前端 `127.0.0.1:8501`
- nginx 反向代理 API 到后端 `127.0.0.1:8766`

因此生产环境建议：
- 对外只放行 `80`（及 `443`，如果启用 HTTPS）
- `8501` 与 `8766` 只在服务器本机可达

## systemd 使用

把模板复制到系统目录后，按实际路径改：
- `User=`
- `WorkingDirectory=`
- `EnvironmentFile=`
- `ExecStart=`

然后：

```bash
sudo cp Deployer/systemd/xiexin-backend.service /etc/systemd/system/
sudo cp Deployer/systemd/xiexin-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable xiexin-backend xiexin-frontend
sudo systemctl start xiexin-backend xiexin-frontend
```

## nginx 使用

复制模板：

```bash
sudo cp Deployer/nginx/xiexin-da-agent.conf /etc/nginx/sites-available/xiexin-da-agent
sudo ln -s /etc/nginx/sites-available/xiexin-da-agent /etc/nginx/sites-enabled/xiexin-da-agent
sudo nginx -t
sudo systemctl reload nginx
```

## 部署后检查

```bash
bash Deployer/healthcheck.sh
```

建议至少检查：
- [http://127.0.0.1:8501](http://127.0.0.1:8501)
- [http://127.0.0.1:8766/health](http://127.0.0.1:8766/health)
- [http://127.0.0.1/health](http://127.0.0.1/health)

## 注意

- `.env` 不要提交到仓库
- 如果服务器启用了 UFW，建议仅放行 `80`（和 `443`）
- 如果只想内网访问，可只放行内网网段
