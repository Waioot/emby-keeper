from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List

import tomlkit

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from embykeeper.config import config as ek_config
from embykeeper.xigua_support import config_file_enables_xigua

DEFAULT_RUNTIME_STATE: Dict[str, Any] = {
    "schedule_enabled": False,
    "mode": "idle",
    "pid": None,
    "last_started_at": None,
    "last_stopped_at": None,
    "last_exit_code": None,
}


def ensure_basedir(basedir: Path) -> Path:
    basedir = Path(basedir).expanduser().resolve()
    basedir.mkdir(parents=True, exist_ok=True)
    (basedir / "logs").mkdir(parents=True, exist_ok=True)
    (basedir / "xigua").mkdir(parents=True, exist_ok=True)
    return basedir


def get_config_path(basedir: Path) -> Path:
    return ensure_basedir(basedir) / "config.toml"


def get_runtime_state_path(basedir: Path) -> Path:
    return ensure_basedir(basedir) / "runtime.json"


def load_runtime_state(basedir: Path) -> Dict[str, Any]:
    path = get_runtime_state_path(basedir)
    state = DEFAULT_RUNTIME_STATE.copy()
    if path.exists():
        try:
            state.update(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return state


def save_runtime_state(basedir: Path, state: Dict[str, Any]) -> Dict[str, Any]:
    payload = DEFAULT_RUNTIME_STATE.copy()
    payload.update(state)
    get_runtime_state_path(basedir).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def update_runtime_state(basedir: Path, **updates) -> Dict[str, Any]:
    state = load_runtime_state(basedir)
    state.update(updates)
    return save_runtime_state(basedir, state)


def read_config_file(basedir: Path) -> str:
    config_path = get_config_path(basedir)
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    return config_path.read_text(encoding="utf-8")


def write_config_file(basedir: Path, data: str) -> str:
    parsed = tomllib.loads(data)
    if not ek_config.validate_config(parsed):
        raise ValueError("配置验证失败")
    clean_data = tomlkit.dumps(parsed)
    get_config_path(basedir).write_text(clean_data, encoding="utf-8")
    return clean_data


def resolve_cli_command() -> List[str]:
    explicit_path = os.environ.get("EK_CLI_PATH", "").strip()
    if explicit_path:
        return _path_to_command(Path(explicit_path).expanduser())

    candidates = []
    argv0 = Path(sys.argv[0]).expanduser()
    if argv0.exists():
        argv0 = argv0.resolve()
        candidates.extend([argv0.parent / "embykeeper", argv0.parent / "cli.py"])

    repo_root = Path(__file__).resolve().parents[1]
    candidates.extend([repo_root / "embykeeper", repo_root / "cli.py"])

    for candidate in candidates:
        if candidate.exists():
            return _path_to_command(candidate)

    discovered = shutil.which("embykeeper")
    if discovered:
        return [discovered]

    raise FileNotFoundError("未找到 embykeeper 可执行文件")


def _path_to_command(path: Path) -> List[str]:
    path = path.expanduser().resolve()
    if path.suffix == ".py":
        return [sys.executable, str(path)]
    return [str(path)]


def sanitize_cli_args(args: List[str]) -> List[str]:
    sanitized: List[str] = []
    skip_next = False
    for idx, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg in {"-B", "--basedir"}:
            skip_next = True
            continue
        if arg.startswith("--basedir="):
            continue
        if arg in {"-i", "-I", "--instant", "--no-instant", "-o", "-O", "--once", "--cron", "-x", "--xigua-url"}:
            continue
        sanitized.append(arg)
    return sanitized


def latest_log_file(basedir: Path) -> Path | None:
    log_dir = ensure_basedir(basedir) / "logs"
    candidates = sorted(log_dir.glob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def tail_log_lines(basedir: Path, lines: int = 200) -> Dict[str, Any]:
    target = latest_log_file(basedir)
    if not target:
        return {"log_file": None, "text": "", "lines": 0}

    content = target.read_text(encoding="utf-8", errors="ignore").splitlines()
    tail = content[-max(1, lines) :]
    return {"log_file": str(target), "text": "\n".join(tail), "lines": len(tail)}


def should_enable_xigua_for_config(basedir: Path) -> bool:
    return config_file_enables_xigua(get_config_path(basedir))
