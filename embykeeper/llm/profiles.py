from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from embykeeper.config import config


@dataclass
class ResolvedLLMProfile:
    base_url: str
    model: str
    api_key: str
    prompt: Optional[str] = None
    timeout: float = 60.0
    retries: int = 3
    temperature: Optional[float] = None
    image_detail: Optional[str] = "high"


def _strip(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _coalesce_number(value: Any, default: Any):
    if value is None:
        return default
    return value


def get_client_account(client_or_account: Any = None):
    if client_or_account is None:
        return None
    if hasattr(client_or_account, "phone"):
        return client_or_account

    phone = getattr(client_or_account, "phone_number", None)
    if not isinstance(phone, str):
        return None
    phone = phone.replace(" ", "")
    telegram = getattr(config, "telegram", None)
    accounts = getattr(telegram, "account", []) if telegram else []
    for account in accounts or []:
        if (getattr(account, "phone", "") or "").replace(" ", "") == phone:
            return account
    return None


def _profile_to_dict(profile: Any) -> dict:
    if profile is None:
        return {}
    if hasattr(profile, "model_dump"):
        return profile.model_dump(exclude_none=True)
    if isinstance(profile, dict):
        return {k: v for k, v in profile.items() if v is not None}
    return {}


def resolve_profile(name: str = "default", client_or_account: Any = None, required: bool = True):
    llm_config = getattr(config, "llm", None)
    base = _profile_to_dict(getattr(llm_config, "default", None))
    if name != "default":
        base.update(_profile_to_dict(getattr(llm_config, name, None)))

    base_url = _strip(base.get("base_url"))
    model = _strip(base.get("model"))
    api_key = _strip(base.get("api_key"))
    if required and not all((base_url, model, api_key)):
        return None
    if not any((base_url, model, api_key, base.get("prompt"))):
        return None

    return ResolvedLLMProfile(
        base_url=base_url or "",
        model=model or "",
        api_key=api_key or "",
        prompt=_strip(base.get("prompt")),
        timeout=float(_coalesce_number(base.get("timeout"), 60.0)),
        retries=int(_coalesce_number(base.get("retries"), 3)),
        temperature=base.get("temperature"),
        image_detail=_strip(base.get("image_detail")) or "high",
    )
