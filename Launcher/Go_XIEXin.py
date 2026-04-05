from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


DEFAULT_PORT = 8501
DEFAULT_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 8766
START_TIMEOUT_SECONDS = 45
FRONTEND_PID_TEMPLATE = "frontend-{port}.pid"
FRONTEND_STDOUT_TEMPLATE = "frontend-{port}.out.log"
FRONTEND_STDERR_TEMPLATE = "frontend-{port}.err.log"
BACKEND_PID_TEMPLATE = "backend-{port}.pid"
BACKEND_STDOUT_TEMPLATE = "backend-{port}.out.log"
BACKEND_STDERR_TEMPLATE = "backend-{port}.err.log"
LAUNCHER_LOG_NAME = "go_xiexin.log"
RUNTIME_DIR_NAME = ".runtime"
FRONTEND_DIR = Path("Gateway") / "Front" / "react-ui"
BACKEND_SCRIPT = Path("orchestrator.py")
CREATE_NO_WINDOW = 0x08000000


def normalize_frontend_path(frontend_path: str = "") -> str:
    path = (frontend_path or "").strip()
    if not path:
        return ""
    path = "/" + path.lstrip("/")
    if path != "/" and not path.endswith("/"):
        path += "/"
    return "" if path == "/" else path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resolve_repo_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def runtime_paths(repo_root: Path, port: int) -> dict[str, Path]:
    runtime_dir = repo_root / RUNTIME_DIR_NAME
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return {
        "runtime_dir": runtime_dir,
        "frontend_pid_file": runtime_dir / FRONTEND_PID_TEMPLATE.format(port=port),
        "frontend_stdout_log": runtime_dir / FRONTEND_STDOUT_TEMPLATE.format(port=port),
        "frontend_stderr_log": runtime_dir / FRONTEND_STDERR_TEMPLATE.format(port=port),
        "backend_pid_file": runtime_dir / BACKEND_PID_TEMPLATE.format(port=DEFAULT_BACKEND_PORT),
        "backend_stdout_log": runtime_dir / BACKEND_STDOUT_TEMPLATE.format(port=DEFAULT_BACKEND_PORT),
        "backend_stderr_log": runtime_dir / BACKEND_STDERR_TEMPLATE.format(port=DEFAULT_BACKEND_PORT),
        "launcher_log": runtime_dir / LAUNCHER_LOG_NAME,
    }


def configure_logging(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("go_xiexin")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def show_messagebox(title: str, message: str, error: bool = False) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if error:
            messagebox.showerror(title, message, parent=root)
        else:
            messagebox.showinfo(title, message, parent=root)
        root.destroy()
    except Exception:
        return


def resolve_python(repo_root: Path, override: str = "") -> Path | None:
    if override:
        candidate = Path(override).expanduser().resolve()
        if candidate.exists():
            return candidate

    if not is_frozen():
        executable = Path(sys.executable)
        if executable.exists() and executable.name.lower() == "python.exe":
            return executable

    for env_name in (".venv311", ".venv", "venv", ".venv312", ".venv310"):
        candidate = repo_root / env_name / "Scripts" / "python.exe"
        if candidate.exists():
            return candidate

    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        candidate = Path(conda_prefix) / "python.exe"
        if candidate.exists():
            return candidate

    which_python = shutil.which("python")
    if which_python:
        return Path(which_python).resolve()

    return None


def resolve_npm() -> Path | None:
    for candidate_name in ("npm.cmd", "npm"):
        resolved = shutil.which(candidate_name)
        if resolved:
            return Path(resolved).resolve()
    return None


def write_pid(pid_file: Path, pid: int) -> None:
    pid_file.write_text(str(pid), encoding="ascii")


def read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    raw = pid_file.read_text(encoding="ascii", errors="ignore").strip()
    if raw.isdigit():
        return int(raw)
    return None


def taskkill_pid(pid: int, logger: logging.Logger) -> bool:
    result = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    success = result.returncode == 0
    logger.info("taskkill pid=%s success=%s stdout=%s stderr=%s", pid, success, result.stdout.strip(), result.stderr.strip())
    return success


def find_listening_pids(port: int) -> list[int]:
    result = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    pids: set[int] = set()
    port_suffix = f":{port}"
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        proto, local_address, _, state, pid_text = parts[:5]
        if proto.upper() != "TCP":
            continue
        if not local_address.endswith(port_suffix):
            continue
        if state.upper() != "LISTENING":
            continue
        if pid_text.isdigit():
            pids.add(int(pid_text))
    return sorted(pids)


def stop_existing_frontend(port: int, pid_file: Path, logger: logging.Logger) -> None:
    killed_any = False
    pid_from_file = read_pid(pid_file)
    if pid_from_file:
        killed_any = taskkill_pid(pid_from_file, logger) or killed_any

    for pid in find_listening_pids(port):
        killed_any = taskkill_pid(pid, logger) or killed_any

    if pid_file.exists():
        pid_file.unlink(missing_ok=True)

    if killed_any:
        time.sleep(1.0)


def stop_process_slot(port: int, pid_file: Path, logger: logging.Logger) -> None:
    stop_existing_frontend(port, pid_file, logger)


def is_http_ready(url: str, timeout_seconds: float = 2.0) -> bool:
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            return 200 <= getattr(response, "status", 0) < 500
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def wait_for_frontend(url: str, process: subprocess.Popen[bytes], timeout_seconds: int, logger: logging.Logger) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            logger.error("frontend process exited early with code %s", process.returncode)
            return False
        if is_http_ready(url):
            logger.info("frontend ready at %s", url)
            return True
        time.sleep(0.5)
    logger.error("frontend did not become ready within %s seconds", timeout_seconds)
    return False


def open_browser(url: str, logger: logging.Logger) -> None:
    opened = webbrowser.open(url, new=2)
    logger.info("browser open requested url=%s opened=%s", url, opened)


def read_log_tail(log_path: Path, max_chars: int = 2000) -> str:
    if not log_path.exists():
        return ""
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def ensure_frontend_dependencies(
    frontend_dir: Path,
    npm_path: Path,
    env: dict[str, str],
    stdout_log: Path,
    stderr_log: Path,
    logger: logging.Logger,
) -> tuple[bool, str]:
    node_modules_dir = frontend_dir / "node_modules"
    vite_binary = node_modules_dir / ".bin" / ("vite.cmd" if os.name == "nt" else "vite")
    if node_modules_dir.exists() and vite_binary.exists():
        logger.info("frontend dependencies already installed")
        return True, ""

    install_command = [str(npm_path), "ci"] if (frontend_dir / "package-lock.json").exists() else [str(npm_path), "install"]
    logger.info("installing frontend dependencies command=%s cwd=%s", install_command, frontend_dir)

    with stdout_log.open("ab") as stdout_handle, stderr_log.open("ab") as stderr_handle:
        result = subprocess.run(
            install_command,
            cwd=frontend_dir,
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )

    if result.returncode != 0:
        logger.error("frontend dependency install failed with code=%s", result.returncode)
        details = read_log_tail(stderr_log) or read_log_tail(stdout_log) or "No dependency installation logs were captured."
        return False, details

    if not vite_binary.exists():
        logger.error("frontend dependency install finished but vite binary is still missing")
        details = read_log_tail(stderr_log) or read_log_tail(stdout_log) or "Vite was still missing after installing dependencies."
        return False, details

    logger.info("frontend dependencies installed successfully")
    return True, ""


def start_frontend(repo_root: Path, port: int, python_override: str, launch_browser: bool, frontend_path: str = "") -> int:
    paths = runtime_paths(repo_root, port)
    logger = configure_logging(paths["launcher_log"])
    frontend_dir = repo_root / FRONTEND_DIR
    backend_script = repo_root / BACKEND_SCRIPT

    logger.info("launcher start requested port=%s repo_root=%s frozen=%s", port, repo_root, is_frozen())

    if not frontend_dir.exists():
        message = f"React frontend not found: {frontend_dir}"
        logger.error(message)
        show_messagebox("Go_XIEXin", message, error=True)
        return 1

    if not backend_script.exists():
        message = f"Backend script not found: {backend_script}"
        logger.error(message)
        show_messagebox("Go_XIEXin", message, error=True)
        return 1

    python_path = resolve_python(repo_root, override=python_override)
    if python_path is None:
        message = "No Python interpreter was found. Create the project venv or pass --python."
        logger.error(message)
        show_messagebox("Go_XIEXin", message, error=True)
        return 1

    npm_path = resolve_npm()
    if npm_path is None:
        message = "No npm executable was found. Install Node.js 20+ and ensure npm is available in PATH."
        logger.error(message)
        show_messagebox("Go_XIEXin", message, error=True)
        return 1

    frontend_url = f"http://{DEFAULT_HOST}:{port}"
    browser_url = f"{frontend_url}{normalize_frontend_path(frontend_path)}"
    backend_url = f"http://{DEFAULT_HOST}:{DEFAULT_BACKEND_PORT}/health"
    if is_http_ready(frontend_url) and is_http_ready(backend_url):
        logger.info("frontend already healthy, reusing existing instance")
        if launch_browser:
            open_browser(browser_url, logger)
        return 0

    stop_process_slot(port, paths["frontend_pid_file"], logger)
    stop_process_slot(DEFAULT_BACKEND_PORT, paths["backend_pid_file"], logger)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    logger.info("starting orchestrator backend with python=%s script=%s", python_path, backend_script)
    with paths["backend_stdout_log"].open("ab") as backend_stdout_handle, paths["backend_stderr_log"].open("ab") as backend_stderr_handle:
        backend_process = subprocess.Popen(
            [
                str(python_path),
                str(backend_script),
                "--serve",
                "--host",
                "0.0.0.0",
                "--port",
                str(DEFAULT_BACKEND_PORT),
            ],
            cwd=repo_root,
            env=env,
            stdout=backend_stdout_handle,
            stderr=backend_stderr_handle,
            creationflags=CREATE_NO_WINDOW,
        )

    write_pid(paths["backend_pid_file"], backend_process.pid)
    logger.info("backend process started pid=%s", backend_process.pid)

    if not wait_for_frontend(backend_url, backend_process, START_TIMEOUT_SECONDS, logger):
        stderr_tail = read_log_tail(paths["backend_stderr_log"])
        stdout_tail = read_log_tail(paths["backend_stdout_log"])
        details = stderr_tail or stdout_tail or "No backend startup logs were captured."
        message = (
            "Go_XIEXin could not start the backend service.\n\n"
            f"Logs: {paths['backend_stderr_log']}\n\n"
            f"Recent output:\n{details}"
        )
        show_messagebox("Go_XIEXin", message, error=True)
        return 1

    install_ok, install_details = ensure_frontend_dependencies(
        frontend_dir=frontend_dir,
        npm_path=npm_path,
        env=env,
        stdout_log=paths["frontend_stdout_log"],
        stderr_log=paths["frontend_stderr_log"],
        logger=logger,
    )
    if not install_ok:
        message = (
            "Go_XIEXin could not install frontend dependencies.\n\n"
            f"Logs: {paths['frontend_stderr_log']}\n\n"
            f"Recent output:\n{install_details}"
        )
        show_messagebox("Go_XIEXin", message, error=True)
        return 1

    logger.info("starting react frontend with npm=%s dir=%s", npm_path, frontend_dir)
    with paths["frontend_stdout_log"].open("ab") as stdout_handle, paths["frontend_stderr_log"].open("ab") as stderr_handle:
        process = subprocess.Popen(
            [
                str(npm_path),
                "run",
                "dev",
                "--",
                "--host",
                "0.0.0.0",
                "--port",
                str(port),
            ],
            cwd=frontend_dir,
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=CREATE_NO_WINDOW,
        )

    write_pid(paths["frontend_pid_file"], process.pid)
    logger.info("frontend process started pid=%s", process.pid)

    if not wait_for_frontend(frontend_url, process, START_TIMEOUT_SECONDS, logger):
        stderr_tail = read_log_tail(paths["frontend_stderr_log"])
        stdout_tail = read_log_tail(paths["frontend_stdout_log"])
        details = stderr_tail or stdout_tail or "No startup logs were captured."
        message = (
            "Go_XIEXin could not start the frontend.\n\n"
            f"Logs: {paths['frontend_stderr_log']}\n\n"
            f"Recent output:\n{details}"
        )
        show_messagebox("Go_XIEXin", message, error=True)
        return 1

    if launch_browser:
        open_browser(browser_url, logger)

    return 0


def stop_frontend(repo_root: Path, port: int) -> int:
    paths = runtime_paths(repo_root, port)
    logger = configure_logging(paths["launcher_log"])
    logger.info("launcher stop requested port=%s", port)
    stop_process_slot(port, paths["frontend_pid_file"], logger)
    stop_process_slot(DEFAULT_BACKEND_PORT, paths["backend_pid_file"], logger)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start or stop xiexin-da-agent.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--python", default="", help="Optional python.exe override.")
    parser.add_argument("--stop", action="store_true", help="Stop the running frontend for the selected port.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser after startup.")
    parser.add_argument("--wechat", action="store_true", help="Deprecated compatibility flag. Startup no longer switches frontend entry.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root()
    if args.stop:
        return stop_frontend(repo_root, args.port)
    return start_frontend(
        repo_root=repo_root,
        port=args.port,
        python_override=args.python,
        launch_browser=not args.no_browser,
        frontend_path="",
    )


if __name__ == "__main__":
    raise SystemExit(main())