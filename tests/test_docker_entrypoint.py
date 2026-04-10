import json
import os
import subprocess
from pathlib import Path


def write_executable(path: Path, text: str):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def test_docker_entrypoint_bootstraps_runtime_files(tmp_path):
    bindir = tmp_path / "bin"
    basedir = tmp_path / "app"
    output = tmp_path / "web-args.txt"
    bindir.mkdir()
    basedir.mkdir()

    write_executable(
        bindir / "embykeeper",
        """#!/usr/bin/env bash
if [[ "${1:-}" == "--example-config" ]]; then
  cat <<'EOF'
[checkiner]
interval_days = 1
EOF
  exit 0
fi
echo "$@" > "${ENTRYPOINT_CLI_ARGS_FILE}"
""",
    )
    write_executable(
        bindir / "embykeeper-web",
        """#!/usr/bin/env bash
echo "$@" > "${ENTRYPOINT_WEB_ARGS_FILE}"
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bindir}:{env['PATH']}",
            "EK_BASEDIR": str(basedir),
            "EK_WEBPASS": "embykeeper",
            "ENTRYPOINT_CLI_ARGS_FILE": str(tmp_path / "cli-args.txt"),
            "ENTRYPOINT_WEB_ARGS_FILE": str(output),
        }
    )

    subprocess.run(
        ["bash", str(Path.cwd() / "scripts/docker-entrypoint.sh")],
        cwd=Path.cwd(),
        env=env,
        check=True,
    )

    assert (basedir / "config.toml").read_text(encoding="utf-8").strip() == "[checkiner]\ninterval_days = 1"
    assert json.loads((basedir / "runtime.json").read_text(encoding="utf-8")) == {
        "schedule_enabled": False,
        "mode": "idle",
        "pid": None,
        "last_started_at": None,
        "last_stopped_at": None,
        "last_exit_code": None,
    }
    assert (basedir / "logs").is_dir()
    assert (basedir / "xigua").is_dir()
    assert output.read_text(encoding="utf-8").strip() == f"--basedir {basedir} --wait"


def test_docker_entrypoint_cli_mode_reuses_existing_config(tmp_path):
    bindir = tmp_path / "bin"
    basedir = tmp_path / "app"
    output = tmp_path / "cli-args.txt"
    bindir.mkdir()
    basedir.mkdir()
    (basedir / "config.toml").write_text("[checkiner]\ninterval_days = 2\n", encoding="utf-8")

    write_executable(
        bindir / "embykeeper",
        """#!/usr/bin/env bash
if [[ "${1:-}" == "--example-config" ]]; then
  echo "should-not-run" > "${ENTRYPOINT_BOOTSTRAP_MARKER}"
  exit 0
fi
echo "$@" > "${ENTRYPOINT_CLI_ARGS_FILE}"
""",
    )
    write_executable(
        bindir / "embykeeper-web",
        """#!/usr/bin/env bash
echo "$@" > "${ENTRYPOINT_WEB_ARGS_FILE}"
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bindir}:{env['PATH']}",
            "EK_BASEDIR": str(basedir),
            "ENTRYPOINT_BOOTSTRAP_MARKER": str(tmp_path / "marker.txt"),
            "ENTRYPOINT_CLI_ARGS_FILE": str(output),
            "ENTRYPOINT_WEB_ARGS_FILE": str(tmp_path / "web-args.txt"),
        }
    )
    env.pop("EK_WEBPASS", None)

    subprocess.run(
        ["bash", str(Path.cwd() / "scripts/docker-entrypoint.sh"), "-i", "-o"],
        cwd=Path.cwd(),
        env=env,
        check=True,
    )

    assert not (tmp_path / "marker.txt").exists()
    assert (basedir / "config.toml").read_text(encoding="utf-8") == "[checkiner]\ninterval_days = 2\n"
    assert output.read_text(encoding="utf-8").strip() == f"--basedir {basedir} -i -o"
