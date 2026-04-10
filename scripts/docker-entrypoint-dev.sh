#!/bin/bash

set -e

EK_BASEDIR="${EK_BASEDIR:-/app}"
EK_CLI_BIN="${EK_CLI_BIN:-$(command -v embykeeper || true)}"

if [ -d "/src" ]; then
    if [ ! "$(ls -A /src)" ]; then
        cp -rT /build /src
    fi
    echo ">> 正在根据源码配置程序, 请稍候."
    pip install --no-cache-dir -e /src
    echo ">> 已配置完成."
    echo
else
    echo ">> 请挂载目录 /src, 以释放源码."
    exit 1
fi

bootstrap_runtime_files() {
    mkdir -p "${EK_BASEDIR}" "${EK_BASEDIR}/logs" "${EK_BASEDIR}/xigua"

    if [ ! -s "${EK_BASEDIR}/config.toml" ]; then
        "${EK_CLI_BIN}" --example-config > "${EK_BASEDIR}/config.toml"
    fi

    if [ ! -f "${EK_BASEDIR}/runtime.json" ]; then
        cat > "${EK_BASEDIR}/runtime.json" <<'EOF'
{
  "schedule_enabled": false,
  "mode": "idle",
  "pid": null,
  "last_started_at": null,
  "last_stopped_at": null,
  "last_exit_code": null
}
EOF
    fi
}

bootstrap_runtime_files

if [ -z "${EK_WEBPASS}" ]; then
    exec "embykeeper" "--basedir" "${EK_BASEDIR}" "$@"
else
    exec "embykeeper-web" "--basedir" "${EK_BASEDIR}" "--wait" "$@"
fi
