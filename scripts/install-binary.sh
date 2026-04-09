#!/usr/bin/env bash

set -euo pipefail

APP_DIR_NAME="${EK_APP_DIR_NAME:-embykeeper-deploy}"
INSTALL_DIR="${PWD}/${APP_DIR_NAME}"
BIN_NAME="${EK_BIN_NAME:-embykeeper}"
WEB_BIN_NAME="${EK_WEB_BIN_NAME:-embykeeper-web}"
CONFIG_FILE="${INSTALL_DIR}/config.toml"
RUNTIME_FILE="${INSTALL_DIR}/runtime.json"
SHA256SUMS_FILE="${INSTALL_DIR}/SHA256SUMS"

sha256_file() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
    return 0
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
    return 0
  fi
  echo "缺少 sha256sum 或 shasum，无法校验下载文件。" >&2
  exit 1
}

detect_os() {
  case "${EK_FORCE_OS:-$(uname -s)}" in
    Linux|linux) echo "linux" ;;
    *)
      echo "当前安装脚本只支持 Linux。" >&2
      exit 1
      ;;
  esac
}

detect_arch() {
  case "${EK_FORCE_ARCH:-$(uname -m)}" in
    x86_64|amd64) echo "amd64" ;;
    *)
      echo "当前安装脚本只支持 amd64。" >&2
      exit 1
      ;;
  esac
}

download_file() {
  local url="$1"
  local target="$2"
  local executable="${3:-false}"
  local temp_file
  temp_file="$(mktemp "${target}.tmp.XXXXXX")"
  curl -fsSL "$url" -o "$temp_file"
  if [[ "$executable" == "true" ]]; then
    chmod +x "$temp_file"
  fi
  mv "$temp_file" "$target"
}

verify_asset() {
  local asset_name="$1"
  local file_path="$2"
  local expected actual

  expected="$(awk -v name="$asset_name" '$2 == name { print $1 }' "$SHA256SUMS_FILE")"
  if [[ -z "$expected" ]]; then
    echo "校验失败: SHA256SUMS 中没有 $asset_name。" >&2
    exit 1
  fi

  actual="$(sha256_file "$file_path")"
  if [[ "$expected" != "$actual" ]]; then
    echo "校验失败: $asset_name 的 sha256 不匹配。" >&2
    exit 1
  fi
}

create_config() {
  if [[ -f "$CONFIG_FILE" ]]; then
    return 0
  fi

  if "$INSTALL_DIR/$BIN_NAME" --example-config > "${CONFIG_FILE}.tmp" 2>/dev/null; then
    mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    return 0
  fi

  cat > "$CONFIG_FILE" <<'CFGEOF'
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
CFGEOF
}

create_runtime_file() {
  if [[ -f "$RUNTIME_FILE" ]]; then
    return 0
  fi

  cat > "$RUNTIME_FILE" <<'CFGEOF'
{
  "schedule_enabled": false,
  "mode": "idle",
  "pid": null,
  "last_started_at": null,
  "last_stopped_at": null,
  "last_exit_code": null
}
CFGEOF
}

main() {
  local os_name arch_name release_root bin_asset web_bin_asset bin_url web_bin_url sha_url

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

  bin_asset="${BIN_NAME}-${os_name}-${arch_name}"
  web_bin_asset="${WEB_BIN_NAME}-${os_name}-${arch_name}"
  bin_url="${EK_BINARY_URL:-${release_root}/${bin_asset}}"
  web_bin_url="${EK_WEB_BINARY_URL:-${release_root}/${web_bin_asset}}"
  sha_url="${EK_SHA256SUMS_URL:-${release_root}/SHA256SUMS}"

  echo ">> 安装目录: $INSTALL_DIR"
  echo ">> 下载校验文件: $sha_url"
  download_file "$sha_url" "$SHA256SUMS_FILE"

  echo ">> 下载主程序: $bin_url"
  download_file "$bin_url" "$INSTALL_DIR/$bin_asset" true
  verify_asset "$bin_asset" "$INSTALL_DIR/$bin_asset"
  mv "$INSTALL_DIR/$bin_asset" "$INSTALL_DIR/$BIN_NAME"

  echo ">> 下载 Web 程序: $web_bin_url"
  download_file "$web_bin_url" "$INSTALL_DIR/$web_bin_asset" true
  verify_asset "$web_bin_asset" "$INSTALL_DIR/$web_bin_asset"
  mv "$INSTALL_DIR/$web_bin_asset" "$INSTALL_DIR/$WEB_BIN_NAME"

  echo ">> 生成配置文件: $CONFIG_FILE"
  create_config
  create_runtime_file
  rm -f "$SHA256SUMS_FILE"

  echo
  echo "安装完成。"
  echo "目录: $INSTALL_DIR"
  echo "主程序: $INSTALL_DIR/$BIN_NAME"
  echo "Web 程序: $INSTALL_DIR/$WEB_BIN_NAME"
  echo "配置文件: $CONFIG_FILE"
  echo "运行状态: $RUNTIME_FILE"
  echo
  echo "后续运行时，请固定使用这个目录作为 basedir。"
  echo "示例："
  echo "  cd \"$INSTALL_DIR\""
  echo "  EK_BASEDIR=\"$INSTALL_DIR\" EK_WEBPASS='请改成你自己的登录密码' EK_XIGUA_API_TOKEN='请改成你自己的密钥' ./$WEB_BIN_NAME --wait --port 1818"
}

main "$@"
