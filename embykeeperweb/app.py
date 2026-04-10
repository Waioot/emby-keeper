from eventlet.patcher import monkey_patch

try:
    monkey_patch()
except RuntimeError as e:
    if "config not loaded" not in str(e):
        raise

import atexit
import base64
import binascii
from datetime import datetime, timezone
import os
from pathlib import Path
import pty
import select
import fcntl
import re
import signal
import struct
from subprocess import Popen, PIPE
import termios
import threading
import time

import tomlkit
import typer
from loguru import logger
from flask import Flask, render_template, request, redirect, url_for, jsonify, Blueprint
from flask_socketio import SocketIO
from flask_login import LoginManager, login_user, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from embykeeper.cache import cache as ek_cache
from embykeeper.xigua_result import load_xigua_result

from . import __version__
from .runtime import (
    ensure_basedir,
    get_config_path,
    load_runtime_state,
    read_config_file,
    resolve_cli_command,
    sanitize_cli_args,
    should_enable_xigua_for_config,
    tail_log_lines,
    update_runtime_state,
    write_config_file,
)

cli = typer.Typer()
app = Flask(__name__, static_folder="templates/assets", static_url_path=None)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
app.config["SECRET_KEY"] = os.urandom(24)
app.config["BASE_PREFIX"] = "/"

socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "main.login"

app.config["lock"] = threading.Lock()
app.config["args"] = []
app.config["fd"] = None
app.config["proc"] = None
app.config["proc_mode"] = None
app.config["manual_stop"] = False
app.config["hist"] = ""
app.config["faillog"] = []
app.config["config"] = ""
app.config["mongodb"] = ""
app.config["webpass"] = ""
app.config["basedir"] = None
app.config["cli_command"] = None
app.config["public_mode"] = False

version = f"V{__version__}"
bp = Blueprint("main", __name__)


class DummyUser:
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return 0


@login_manager.user_loader
def load_user(_):
    return DummyUser()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def exit_handler():
    proc = app.config["proc"]
    if proc:
        kill_proc(proc)


@bp.route("/")
def index():
    return redirect(url_for("main.console"))


@bp.route("/console")
@login_required
def console():
    return render_template("console.html", version=version, prefix=app.config["BASE_PREFIX"])


@bp.route("/login", methods=["GET"])
def login():
    return render_template("login.html", version=version, prefix=app.config["BASE_PREFIX"])


@bp.route("/login", methods=["POST"])
def login_submit():
    password = request.form.get("password", "")
    webpass = app.config.get("webpass", "")
    if not webpass:
        emsg = "后台没有设置控制台密码, 无法登录."
    elif sum(t > time.time() - 3600 for t in app.config["faillog"][-5:]) == 5:
        emsg = "一小时内有过多次失败登录, 请稍后再试."
    else:
        if password == webpass:
            login_user(DummyUser())
            return redirect(request.args.get("next") or url_for("main.index"))
        emsg = "密码错误, 请重试."
        app.config["faillog"].append(time.time())
    return render_template("login.html", emsg=emsg, version=version, prefix=app.config["BASE_PREFIX"])


@bp.route("/config", methods=["GET"])
@login_required
def config():
    return render_template(
        "config.html",
        version=version,
        prefix=app.config["BASE_PREFIX"],
        config_path=str(get_config_path(get_runtime_basedir())),
        file_config_mode=is_file_config_mode(),
    )


@bp.route("/config/current", methods=["GET"])
def config_current():
    if not is_authenticated():
        return "Not authenticated", 401
    try:
        data = load_config_text()
    except FileNotFoundError:
        return "Config missing", 404
    except ValueError:
        return "Config malformed", 400
    return jsonify(data), 200


@bp.route("/config/example", methods=["GET"])
def config_example():
    if not is_authenticated():
        return "Not authenticated", 401
    command = [*app.config["cli_command"], "--example-config"]
    example, _ = Popen(command, stdout=PIPE, text=True).communicate()
    return jsonify(example), 200


@bp.route("/config/save", methods=["POST"])
def config_save():
    if not is_authenticated():
        return "Not authenticated", 401
    payload = request.get_json() or {}
    data = payload.get("config", "")
    try:
        clean_data = save_config_text(data)
    except tomllib.TOMLDecodeError as exc:
        return jsonify({"ok": False, "error": f"配置文件 TOML 格式错误: {exc}"}), 400
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    if is_file_config_mode():
        return (
            jsonify(
                {
                    "ok": True,
                    "message": f'配置已写入 "{get_config_path(get_runtime_basedir())}"。',
                    "path": str(get_config_path(get_runtime_basedir())),
                    "config": clean_data,
                }
            ),
            200,
        )

    return jsonify({"ok": True, "config": clean_data}), 200


@bp.route("/healthz")
def healthz():
    return "200 OK"


@bp.route("/heartbeat")
def heartbeat():
    if not is_authenticated():
        return "Not authenticated", 401
    return jsonify(get_runtime_status_payload()), 200


@bp.route("/api/runtime/status", methods=["GET"])
def runtime_status():
    if not is_authenticated():
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    return jsonify(get_runtime_status_payload()), 200


@bp.route("/api/runtime/run-once", methods=["POST"])
def runtime_run_once():
    if not is_authenticated():
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    if is_proc_running():
        return jsonify({"ok": False, "error": "当前已有任务正在运行"}), 409

    try:
        start_proc("run-once", clear_history=True)
    except FileNotFoundError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, "status": get_runtime_status_payload()}), 202


@bp.route("/api/runtime/schedule/start", methods=["POST"])
def runtime_schedule_start():
    if not is_authenticated():
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    if is_proc_running():
        return jsonify({"ok": False, "error": "当前已有任务正在运行"}), 409

    try:
        start_proc("scheduled", clear_history=True)
    except FileNotFoundError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, "status": get_runtime_status_payload()}), 202


@bp.route("/api/runtime/schedule/stop", methods=["POST"])
def runtime_schedule_stop():
    if not is_authenticated():
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    stop_current_proc(disable_schedule=True)
    return jsonify({"ok": True, "status": get_runtime_status_payload()}), 200


@bp.route("/api/logs/tail", methods=["GET"])
def logs_tail():
    if not is_authenticated():
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    try:
        lines = min(max(int(request.args.get("lines", 200)), 1), 1000)
    except ValueError:
        lines = 200
    payload = tail_log_lines(get_runtime_basedir(), lines=lines)
    payload["ok"] = True
    return jsonify(payload), 200


@bp.route("/api/xigua/latest", methods=["GET"])
def xigua_latest():
    if not is_xigua_api_authenticated():
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    return jsonify(load_xigua_result(get_runtime_basedir())), 200


@app.errorhandler(404)
def page_not_found(_):
    return render_template("404.html", version=version, prefix=app.config["BASE_PREFIX"]), 404


@socketio.on("pty-input", namespace="/pty")
def pty_input(data):
    if not is_authenticated():
        return
    with app.config["lock"]:
        if app.config["fd"]:
            os.write(app.config["fd"], data["input"].encode())


@socketio.on("resize", namespace="/pty")
def resize(data):
    logger.debug("Received resize socketio signal.")
    if not is_authenticated():
        return
    with app.config["lock"]:
        if app.config["fd"]:
            set_size(app.config["fd"], data["rows"], data["cols"])


@socketio.on("connect", namespace="/pty")
def handle_connect():
    logger.debug(f"Console connected from {request.sid}")
    socketio.emit("runtime-status", get_runtime_status_payload(), namespace="/pty", to=request.sid)


@socketio.on("disconnect", namespace="/pty")
def handle_disconnect(reason=""):
    logger.debug(f"Console disconnected from {request.sid} ({reason})")


@socketio.on_error_default
def default_error_handler(e):
    logger.error(f"SocketIO error occurred: {str(e)}")


@socketio.on("embykeeper_start", namespace="/pty")
def start(data, auth=True):
    logger.debug(f"Received embykeeper_start socketio signal from {request.sid}.")
    if not is_authenticated():
        logger.debug("Authentication failed.")
        return
    with app.config["lock"]:
        if app.config["fd"] and app.config["proc"] and app.config["proc"].poll() is None:
            set_size(app.config["fd"], data["rows"], data["cols"])
        socketio.sleep(0.1)
        socketio.emit("pty-output", {"output": app.config["hist"]}, namespace="/pty", to=request.sid)
        logger.debug(f"Sent pty-output to {request.sid}, length: {len(app.config['hist'])}.")


@socketio.on("embykeeper_kill", namespace="/pty")
def kill():
    logger.debug("Received embykeeper_kill socketio signal.")
    if not is_authenticated():
        return
    stop_current_proc(disable_schedule=True)


def is_authenticated():
    webpass = app.config.get("webpass", "")
    return (not webpass) or current_user.is_authenticated


def is_xigua_api_authenticated():
    if is_authenticated():
        return True

    token = os.environ.get("EK_XIGUA_API_TOKEN", "").strip()
    if not token:
        return False
    request_token = request.headers.get("X-Xigua-Api-Token", "").strip() or request.args.get("token", "").strip()
    return request_token == token


def get_runtime_basedir() -> Path:
    basedir = app.config.get("basedir")
    if basedir:
        return ensure_basedir(Path(basedir))

    env_basedir = os.environ.get("EK_BASEDIR", "").strip()
    if env_basedir:
        return ensure_basedir(Path(env_basedir))

    return ensure_basedir(Path.cwd())


def is_file_config_mode() -> bool:
    return not (app.config.get("public_mode") or app.config.get("mongodb"))


def load_config_text() -> str:
    if is_file_config_mode():
        return read_config_file(get_runtime_basedir())

    if not app.config["mongodb"]:
        data = app.config["config"]
    else:
        data = ek_cache.get("config", None)

    if not data:
        raise FileNotFoundError("Config missing")

    try:
        return base64.b64decode(re.sub(r"\s+", "", data).encode()).decode()
    except (binascii.Error, UnicodeDecodeError) as exc:
        logger.error(f"Config string malformed: {exc}")
        raise ValueError("Config malformed") from exc


def save_config_text(data: str) -> str:
    if is_file_config_mode():
        return write_config_file(get_runtime_basedir(), data)

    clean_dict = tomllib.loads(data)
    clean_data = tomlkit.dumps(clean_dict)
    encoded_data = base64.b64encode(clean_data.encode()).decode()
    if not app.config["mongodb"]:
        app.config["config"] = encoded_data
    else:
        ek_cache.set("config", encoded_data)
    return clean_data


def should_enable_xigua() -> bool:
    if is_file_config_mode():
        return should_enable_xigua_for_config(get_runtime_basedir())
    return False


def build_cli_args(mode: str) -> list[str]:
    basedir = get_runtime_basedir()
    args = [*app.config["cli_command"]]
    if is_file_config_mode():
        args.append(str(get_config_path(basedir)))

    args.extend(sanitize_cli_args(app.config["args"]))
    args.extend(["-B", str(basedir), "-i"])

    if mode == "run-once":
        args.append("-o")
    if should_enable_xigua():
        args.append("-x")
    return args


def is_proc_running() -> bool:
    proc = app.config.get("proc")
    return proc is not None and proc.poll() is None


def get_runtime_status_payload() -> dict:
    state = load_runtime_state(get_runtime_basedir())
    if is_proc_running():
        state["pid"] = app.config["proc"].pid
        state["mode"] = "scheduled" if app.config.get("proc_mode") == "scheduled" else "running"
    else:
        state["pid"] = None
        state["mode"] = "idle"
    return state


def emit_runtime_status():
    socketio.emit("runtime-status", get_runtime_status_payload(), namespace="/pty")


def read_and_forward_pty_output():
    threading.current_thread().name = "pty_reader"
    max_read_bytes = 1024 * 20
    while True:
        fd = app.config.get("fd")
        if not fd:
            break
        try:
            with app.config["lock"]:
                if not app.config.get("fd"):
                    break
                ready, _, _ = select.select([app.config["fd"]], [], [], 1.0)
                if ready:
                    output = os.read(app.config["fd"], max_read_bytes).decode(errors="ignore")
                    app.config["hist"] += output
                    socketio.emit("pty-output", {"output": output}, namespace="/pty")
        except (select.error, OSError):
            break
    logger.debug("PTY reader task ended")


def restart_scheduled_proc():
    socketio.sleep(1)
    state = load_runtime_state(get_runtime_basedir())
    if state.get("schedule_enabled") and not is_proc_running():
        try:
            start_proc("scheduled", clear_history=False)
        except Exception as exc:
            logger.error(f"重新启动定时任务失败: {exc}")


def disconnect_on_proc_exit(proc: Popen):
    returncode = proc.wait()
    manual_stop = app.config.get("manual_stop", False)
    restart_needed = False

    with app.config["lock"]:
        current_proc = app.config.get("proc")
        if current_proc is proc:
            fd = app.config.get("fd")
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            app.config["fd"] = None
            app.config["proc"] = None
            app.config["proc_mode"] = None
        app.config["manual_stop"] = False
        restart_needed = load_runtime_state(get_runtime_basedir()).get("schedule_enabled", False) and not manual_stop

    update_runtime_state(
        get_runtime_basedir(),
        pid=None,
        mode="idle",
        last_exit_code=returncode,
        last_stopped_at=utc_now_iso(),
    )

    output = f"\r\n\n程序已退出, 返回值 {returncode}.\r\n"
    if restart_needed:
        output += "正在尝试恢复定时任务.\r\n"
        socketio.start_background_task(target=restart_scheduled_proc)
    app.config["hist"] += output
    socketio.emit("pty-output", {"output": output}, namespace="/pty")
    emit_runtime_status()


def start_proc(mode: str, clear_history: bool = True):
    if is_proc_running():
        raise RuntimeError("当前已有任务正在运行")

    basedir = get_runtime_basedir()
    if is_file_config_mode() and not get_config_path(basedir).exists():
        raise FileNotFoundError(f'配置文件不存在: "{get_config_path(basedir)}"')

    master_fd, slave_fd = pty.openpty()
    args = build_cli_args(mode)
    env = {**os.environ, "TZ": "Asia/Shanghai"}
    if not is_file_config_mode():
        env["EK_CONFIG"] = app.config["config"]
        env["EK_MONGODB"] = app.config["mongodb"]

    p = Popen(
        args,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        cwd=str(basedir),
        env=env,
        preexec_fn=os.setsid,
    )

    if clear_history:
        app.config["hist"] = ""
    app.config["fd"] = master_fd
    app.config["proc"] = p
    app.config["proc_mode"] = mode
    app.config["manual_stop"] = False
    update_runtime_state(
        basedir,
        schedule_enabled=(mode == "scheduled"),
        mode="scheduled" if mode == "scheduled" else "running",
        pid=p.pid,
        last_started_at=utc_now_iso(),
    )
    socketio.start_background_task(target=disconnect_on_proc_exit, proc=p)
    socketio.start_background_task(target=read_and_forward_pty_output)
    atexit.register(exit_handler)
    emit_runtime_status()
    logger.debug(f"Embykeeper started at: {p.pid}.")


def stop_current_proc(disable_schedule: bool = True):
    basedir = get_runtime_basedir()
    proc = app.config.get("proc")
    schedule_enabled = load_runtime_state(basedir).get("schedule_enabled", False) and not disable_schedule
    update_runtime_state(
        basedir,
        schedule_enabled=schedule_enabled,
        mode="idle",
        pid=None,
        last_stopped_at=utc_now_iso(),
    )

    if proc is None:
        emit_runtime_status()
        return

    app.config["manual_stop"] = True
    kill_proc(proc)
    emit_runtime_status()


def kill_proc(proc: Popen):
    try:
        proc.send_signal(signal.SIGINT)
        for _ in range(20):
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        logger.debug(f"Embykeeper killed: {proc.pid}.")
    except Exception as e:
        logger.error(f"Error killing process: {e}")


def set_size(fd, row, col, xpix=0, ypix=0):
    logger.debug(f"Resizing pty to: {row} {col}.")
    size = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, size)


def set_static_url_path(webapp, prefix):
    webapp.static_url_path = f"{prefix}/assets"
    webapp.view_functions.pop("static", None)
    webapp.add_url_rule(
        f"{webapp.static_url_path}/<path:filename>", endpoint="static", view_func=webapp.send_static_file
    )


def setup_web_app(prefix: str):
    normalized_prefix = prefix.rstrip("/")
    if app.config.get("_setup_prefix") == normalized_prefix and bp.name in app.blueprints:
        app.config["BASE_PREFIX"] = normalized_prefix
        return

    app.config["BASE_PREFIX"] = normalized_prefix
    if not app._got_first_request:
        set_static_url_path(app, app.config["BASE_PREFIX"])
        if bp.name not in app.blueprints:
            app.register_blueprint(bp, url_prefix=app.config["BASE_PREFIX"])
    app.config["_setup_prefix"] = normalized_prefix


@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
def run(
    ctx: typer.Context,
    port: int = typer.Option(1818, envvar="PORT", show_envvar=False),
    host: str = "0.0.0.0",
    debug: bool = False,
    instant: bool = typer.Option(
        False,
        "--instant/--no-instant",
        "-i/-I",
        envvar="EK_INSTANT",
        show_envvar=False,
        help="启动时先立刻执行一次任务, 若未指定仅执行一次模式则随后继续计划执行",
    ),
    wait: bool = False,
    prefix: str = typer.Option("", envvar="EK_BASE_PREFIX", help="Base URL prefix (e.g. /ek)"),
    basedir: Path = typer.Option(None, "--basedir", "-B", envvar="EK_BASEDIR", help="数据目录"),
):
    app.config["args"] = ctx.args
    app.config["public_mode"] = "--public" in ctx.args
    app.config["config"] = os.environ.get("EK_CONFIG", "")
    app.config["mongodb"] = os.environ.get("EK_MONGODB", "")
    app.config["webpass"] = os.environ.get("EK_WEBPASS", "").strip()
    app.config["basedir"] = ensure_basedir(Path(basedir or Path.cwd()))
    app.config["cli_command"] = resolve_cli_command()

    setup_web_app(prefix)

    state = load_runtime_state(get_runtime_basedir())
    should_start = state.get("schedule_enabled", False) or (not wait)
    if should_start and not is_proc_running():
        start_proc("scheduled", clear_history=True)

    logger.info(f"Embykeeper webserver started at {host}:{port} with prefix {prefix or '/'}")
    socketio.run(app, port=port, host=host, debug=debug)


if __name__ == "__main__":
    cli()
