from __future__ import annotations

from typing import Iterable, Tuple

from embykeeper.notifier.telegram_bot import resolve_bot_token, resolve_chat_id

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
        else:
            missing.append(capability)
    return missing


def check_capabilities(required_capabilities: Iterable[str], client_or_account=None):
    missing = get_missing_capabilities(required_capabilities, client_or_account)
    return not missing, missing


def describe_missing_capability(capability: str) -> Tuple[str, str | None]:
    return capability, None


def format_missing_capabilities(missing_capabilities: Iterable[str]):
    details = []
    for capability in list(missing_capabilities or []):
        name, reason = describe_missing_capability(capability)
        details.append(f"{name} ({reason})" if reason else name)
    return ", ".join(details)
