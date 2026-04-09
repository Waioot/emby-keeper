from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Set

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from .schema import Config, TelegramAccount


def site_selection_includes_xigua(site_names: Optional[Iterable[str]]) -> bool:
    if site_names is None:
        return True

    normalized = [str(name).strip().lower() for name in site_names if str(name).strip()]
    if not normalized:
        return False
    if "xigua" in normalized or "+xigua" in normalized:
        return True
    if "all" in normalized and "-xigua" not in normalized:
        return True
    return False


def get_xigua_enabled_phones(cfg: Config) -> Set[str]:
    phones: Set[str] = set()
    global_sites = cfg.site.checkiner if cfg.site else None

    for account in cfg.telegram.account or []:
        if not account.enabled or not account.checkiner:
            continue
        account_sites = account.site.checkiner if account.site else None
        effective_sites = account_sites if account_sites is not None else global_sites
        if site_selection_includes_xigua(effective_sites):
            phones.add(account.phone)

    return phones


def config_file_enables_xigua(config_path: Path) -> bool:
    if not config_path.exists():
        return False

    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    telegram = raw.get("telegram") or {}
    accounts = telegram.get("account") or []
    global_sites = ((raw.get("site") or {}).get("checkiner"))

    for account in accounts:
        if not account.get("enabled", True) or not account.get("checkiner", True):
            continue
        account_sites = ((account.get("site") or {}).get("checkiner"))
        effective_sites = account_sites if account_sites is not None else global_sites
        if site_selection_includes_xigua(effective_sites):
            return True

    return False
