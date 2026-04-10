import sys
from pathlib import Path

from embykeeperweb.app import app, setup_web_app
from embykeeperweb.runtime import load_runtime_state, resolve_cli_command, update_runtime_state

CONFIG_TEXT = '''
[checkiner]
time_range = "<8:00AM,10:00AM>"
interval_days = "1"
timeout = 120
retries = 4
concurrency = 1
random_start = 60

[[telegram.account]]
phone = "+8611111111111"
checkiner = true
enabled = true

[site]
checkiner = ["xigua"]
'''


def configure_test_app(tmp_path: Path):
    app.config["TESTING"] = True
    app.config["basedir"] = tmp_path
    app.config["webpass"] = "secret"
    app.config["public_mode"] = False
    app.config["mongodb"] = ""
    app.config["config"] = ""
    app.config["proc"] = None
    app.config["proc_mode"] = None
    app.config["fd"] = None
    app.config["hist"] = ""
    app.config["args"] = []
    app.config["manual_stop"] = False
    app.config["cli_command"] = [sys.executable, str(Path.cwd() / "cli.py")]
    setup_web_app("")
    return app.test_client()


def login(client):
    response = client.post("/login", data={"password": "secret"}, follow_redirects=False)
    assert response.status_code == 302


def test_web_requires_login_for_sensitive_routes(tmp_path):
    client = configure_test_app(tmp_path)

    assert client.get("/config/current").status_code == 401
    assert client.post("/api/runtime/run-once").status_code == 401
    assert client.get("/api/logs/tail").status_code == 401


def test_web_can_save_and_read_config_file(tmp_path):
    client = configure_test_app(tmp_path)
    login(client)

    response = client.post("/config/save", json={"config": CONFIG_TEXT})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert Path(payload["path"]).exists()
    assert "配置已写入" in payload["message"]

    current = client.get("/config/current")
    assert current.status_code == 200
    current_text = current.get_json()
    assert '+8611111111111' in current_text
    assert 'checkiner = ["xigua"]' in current_text


def test_config_example_uses_configured_cli_command(tmp_path):
    script = tmp_path / "fake_cli.py"
    script.write_text(
        "import sys\n"
        "if '--example-config' in sys.argv:\n"
        "    print('fake-example-config')\n",
        encoding="utf-8",
    )

    client = configure_test_app(tmp_path)
    app.config["cli_command"] = [sys.executable, str(script)]
    login(client)

    response = client.get("/config/example")
    assert response.status_code == 200
    assert response.get_json() == "fake-example-config\n"


def test_runtime_routes_call_expected_handlers(tmp_path, monkeypatch):
    client = configure_test_app(tmp_path)
    login(client)

    calls = []

    def fake_start(mode, clear_history=True):
        calls.append(("start", mode, clear_history))

    def fake_stop(disable_schedule=True):
        calls.append(("stop", disable_schedule))

    monkeypatch.setattr("embykeeperweb.app.start_proc", fake_start)
    monkeypatch.setattr("embykeeperweb.app.stop_current_proc", fake_stop)
    monkeypatch.setattr(
        "embykeeperweb.app.get_runtime_status_payload",
        lambda: {"mode": "idle", "schedule_enabled": False, "pid": None},
    )

    run_once = client.post("/api/runtime/run-once")
    assert run_once.status_code == 202
    schedule_start = client.post("/api/runtime/schedule/start")
    assert schedule_start.status_code == 202
    schedule_stop = client.post("/api/runtime/schedule/stop")
    assert schedule_stop.status_code == 200

    assert calls == [
        ("start", "run-once", True),
        ("start", "scheduled", True),
        ("stop", True),
    ]


def test_runtime_state_helpers_persist_to_runtime_json(tmp_path):
    update_runtime_state(tmp_path, schedule_enabled=True, mode="scheduled", pid=12345)
    state = load_runtime_state(tmp_path)

    assert state["schedule_enabled"] is True
    assert state["mode"] == "scheduled"
    assert state["pid"] == 12345
    assert (tmp_path / "runtime.json").exists()


def test_xigua_api_allows_logged_in_web_user_when_token_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("EK_XIGUA_API_TOKEN", "demo-token")
    client = configure_test_app(tmp_path)

    unauthorized = client.get("/api/xigua/latest")
    assert unauthorized.status_code == 401

    login(client)
    authenticated = client.get("/api/xigua/latest")
    assert authenticated.status_code == 200
    assert authenticated.get_json()["ok"] is False

    authorized = client.get("/api/xigua/latest?token=demo-token")
    assert authorized.status_code == 200
    assert authorized.get_json()["ok"] is False


def test_resolve_cli_command_prefers_env_path(tmp_path, monkeypatch):
    binary = tmp_path / "embykeeper"
    binary.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("EK_CLI_PATH", str(binary))

    assert resolve_cli_command() == [str(binary.resolve())]
