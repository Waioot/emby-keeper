import asyncio
from types import SimpleNamespace

from embykeeper import var
from embykeeper.schema import TelegramAccount

asyncio.set_event_loop(asyncio.new_event_loop())

from embykeeper.telegram.checkin_main import CheckinerManager


class DummyLog:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(("info", message))

    def warning(self, message):
        self.messages.append(("warning", message))


def test_refresh_xigua_url_for_enabled_account(monkeypatch):
    manager = CheckinerManager()
    account = TelegramAccount(phone="+8611111111111", checkiner=True, enabled=True)
    client = object()
    log = DummyLog()
    calls = {}

    async def fake_fetch(current_client, timeout=15.0):
        calls["client"] = current_client
        calls["timeout"] = timeout
        return "https://example.com"

    monkeypatch.setattr("embykeeper.xigua_url_cli.fetch_xigua_checkin_url_with_client", fake_fetch)
    monkeypatch.setattr("embykeeper.xigua_result.save_xigua_result", lambda **kwargs: calls.setdefault("saved", kwargs))
    var.xigua_url_phone_numbers = {account.phone}

    asyncio.run(manager._refresh_xigua_url_if_needed(account, client, log))

    assert calls["client"] is client
    assert ("info", "已刷新西瓜签到链接。") in log.messages
    var.xigua_url_phone_numbers = set()


def test_refresh_xigua_url_records_error_when_fetch_fails(monkeypatch):
    manager = CheckinerManager()
    account = TelegramAccount(phone="+8611111111111", checkiner=True, enabled=True)
    client = object()
    log = DummyLog()
    saved = {}

    async def fake_fetch(current_client, timeout=15.0):
        raise RuntimeError("boom")

    def fake_save(**kwargs):
        saved.update(kwargs)

    monkeypatch.setattr("embykeeper.xigua_url_cli.fetch_xigua_checkin_url_with_client", fake_fetch)
    monkeypatch.setattr("embykeeper.xigua_result.save_xigua_result", fake_save)
    var.xigua_url_phone_numbers = {account.phone}

    asyncio.run(manager._refresh_xigua_url_if_needed(account, client, log))

    assert saved["error"] == "boom"
    assert any(level == "warning" and "boom" in message for level, message in log.messages)
    var.xigua_url_phone_numbers = set()
