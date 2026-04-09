from datetime import datetime, timezone
import json
from pathlib import Path

from embykeeper.config import config


def get_xigua_result_path(basedir: Path | None = None) -> Path:
    base = Path(basedir or config.basedir)
    target_dir = base / "xigua"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / "latest.json"


def save_xigua_result(url: str | None = None, error: str | None = None, basedir: Path | None = None):
    now = datetime.now(timezone.utc)
    payload = {
        "ok": bool(url),
        "url": url,
        "error": error,
        "generated_at": now.isoformat(),
        "generated_ts": int(now.timestamp()),
    }
    get_xigua_result_path(basedir).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def load_xigua_result(basedir: Path | None = None):
    path = get_xigua_result_path(basedir)
    if not path.exists():
        return {
            "ok": False,
            "url": None,
            "error": "还没有生成过西瓜签到链接",
            "generated_at": None,
            "generated_ts": None,
            "age_seconds": None,
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    generated_ts = payload.get("generated_ts")
    if isinstance(generated_ts, int):
        payload["age_seconds"] = max(0, int(datetime.now(timezone.utc).timestamp()) - generated_ts)
    else:
        payload["age_seconds"] = None
    return payload
