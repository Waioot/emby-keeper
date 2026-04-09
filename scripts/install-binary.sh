#!/usr/bin/env bash

set -euo pipefail

APP_DIR_NAME="${EK_APP_DIR_NAME:-embykeeper-deploy}"
INSTALL_DIR="${PWD}/${APP_DIR_NAME}"
BIN_NAME="${EK_BIN_NAME:-embykeeper}"
WEB_BIN_NAME="${EK_WEB_BIN_NAME:-embykeeper-web}"
CONFIG_FILE="${INSTALL_DIR}/config.toml"

detect_os() {
  case "$(uname -s)" in
    Linux) echo "linux" ;;
    Darwin) echo "darwin" ;;
    *)
      echo "暂不支持当前系统: $(uname -s)" >&2
      exit 1
      ;;
  esac
}

detect_arch() {
  case "$(uname -m)" in
    x86_64|amd64) echo "amd64" ;;
    aarch64|arm64) echo "arm64" ;;
    *)
      echo "暂不支持当前架构: $(uname -m)" >&2
      exit 1
      ;;
  esac
}

download_file() {
  local url="$1"
  local target="$2"
  local temp_file
  temp_file="$(mktemp "${target}.tmp.XXXXXX")"
  curl -fsSL "$url" -o "$temp_file"
  chmod +x "$temp_file"
  mv "$temp_file" "$target"
}

create_config() {
  if [[ -f "$CONFIG_FILE" ]]; then
    return 0
  fi

  if "$INSTALL_DIR/$BIN_NAME" --example-config > "${CONFIG_FILE}.tmp" 2>/dev/null; then
    mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    return 0
  fi

  cat > "$CONFIG_FILE" <<'EOF'
[checkiner]
time_range = "<8:00AM,10:00AM>"
random_start = 60
timeout = 120
retries = 4
concurrency = 1
interval_days = 1

[[telegram.account]]
phone = "+861xxxxxxxxxx"
checkiner = true
monitor = false
messager = false
registrar = false
enabled = true

[site]
checkiner = ["terminus", "xigua"]
EOF
}

main() {
  local os_name arch_name release_root bin_url web_bin_url

  command -v curl >/dev/null 2>&1 || {
    echo "缺少 curl，无法继续安装。" >&2
    exit 1
  }

  os_name="$(detect_os)"
  arch_name="$(detect_arch)"

  mkdir -p "$INSTALL_DIR"
  mkdir -p "$INSTALL_DIR/logs"
  mkdir -p "$INSTALL_DIR/xigua"

  if [[ -n "${EK_RELEASE_ROOT:-}" ]]; then
    release_root="${EK_RELEASE_ROOT}"
  else
    release_root="https://github.com/emby-keeper/emby-keeper/releases/latest/download"
  fi

  bin_url="${EK_BINARY_URL:-${release_root}/${BIN_NAME}-${os_name}-${arch_name}}"
  web_bin_url="${EK_WEB_BINARY_URL:-${release_root}/${WEB_BIN_NAME}-${os_name}-${arch_name}}"

  echo ">> 安装目录: $INSTALL_DIR"
  echo ">> 下载主程序: $bin_url"
  download_file "$bin_url" "$INSTALL_DIR/$BIN_NAME"

  echo ">> 下载 Web 程序: $web_bin_url"
  download_file "$web_bin_url" "$INSTALL_DIR/$WEB_BIN_NAME"

  echo ">> 生成配置文件: $CONFIG_FILE"
  create_config

  echo
  echo "安装完成。"
  echo "目录: $INSTALL_DIR"
  echo "主程序: $INSTALL_DIR/$BIN_NAME"
  echo "Web 程序: $INSTALL_DIR/$WEB_BIN_NAME"
  echo "配置文件: $CONFIG_FILE"
  echo
  echo "后续运行时，请固定使用这个目录作为 basedir。"
  echo "示例："
  echo "  cd \"$INSTALL_DIR\""
  echo "  ./$BIN_NAME ./config.toml -i -o -x -B \"$INSTALL_DIR\""
  echo "  EK_BASEDIR=\"$INSTALL_DIR\" EK_XIGUA_API_TOKEN='请改成你自己的密钥' ./$WEB_BIN_NAME --wait --port 1818"
}

main "$@"
