from __future__ import annotations

from typing import Iterable

from embykeeper.notifier.telegram_bot import resolve_bot_token, resolve_chat_id
from embykeeper.telegram.cf_turnstile import is_solver_available

from .llm.profiles import resolve_profile


def get_missing_capabilities(required_capabilities: Iterable[str], client_or_account=None):
    missing = []
    for capability in required_capabilities or []:
        if capability == "llm.ocr":
            if not resolve_profile("ocr", client_or_account, required=True):
                missing.append(capability)
        elif capability == "llm.vision":
            if not resolve_profile("vision", client_or_account, required=True):
                missing.append(capability)
        elif capability == "llm.text":
            if not resolve_profile("default", client_or_account, required=True):
                missing.append(capability)
        elif capability == "notifier.telegram_bot":
            if not resolve_bot_token() or resolve_chat_id() is None:
                missing.append(capability)
        elif capability == "cf.turnstile":
            if not is_solver_available():
                missing.append(capability)
        else:
            missing.append(capability)
    return missing


def check_capabilities(required_capabilities: Iterable[str], client_or_account=None):
    missing = get_missing_capabilities(required_capabilities, client_or_account)
    return not missing, missing


def format_missing_capabilities(missing_capabilities: Iterable[str]):
    missing = list(missing_capabilities or [])
    if not missing:
        return ""
    return ", ".join(missing)
