import hashlib
import os
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_executable(path: Path, text: str):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def test_install_binary_script_with_local_release(tmp_path):
    release_dir = tmp_path / "release"
    work_dir = tmp_path / "work"
    install_dir = work_dir / "embykeeper-deploy"
    release_dir.mkdir()
    work_dir.mkdir()

    cli_asset = release_dir / "embykeeper-linux-amd64"
    web_asset = release_dir / "embykeeper-web-linux-amd64"
    sums_file = release_dir / "SHA256SUMS"

    write_executable(
        cli_asset,
        """#!/usr/bin/env bash
if [[ "${1:-}" == "--example-config" ]]; then
  cat <<'EOF'
[checkiner]
interval_days = 1
EOF
else
  echo "cli"
fi
""",
    )
    write_executable(
        web_asset,
        """#!/usr/bin/env bash
echo "web"
""",
    )

    sums_file.write_text(
        f"{sha256(cli_asset)}  {cli_asset.name}\n{sha256(web_asset)}  {web_asset.name}\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "EK_RELEASE_ROOT": release_dir.resolve().as_uri(),
            "EK_FORCE_OS": "linux",
            "EK_FORCE_ARCH": "amd64",
        }
    )

    subprocess.run(
        ["bash", str(Path.cwd() / "scripts/install-binary.sh")],
        cwd=work_dir,
        env=env,
        check=True,
    )

    assert (install_dir / "embykeeper").exists()
    assert (install_dir / "embykeeper-web").exists()
    assert (install_dir / "config.toml").exists()
    assert (install_dir / "runtime.json").exists()
    assert (install_dir / "logs").is_dir()
    assert (install_dir / "xigua").is_dir()
    assert not (install_dir / "SHA256SUMS").exists()
