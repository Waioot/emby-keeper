from __future__ import annotations

from .client import chat_completion
from .profiles import resolve_profile


async def infer_text(
    prompt: str,
    client_or_account=None,
    log=None,
    profile_name: str = "default",
    temperature=None,
    timeout=None,
):
    profile = resolve_profile("default" if profile_name == "text" else profile_name, client_or_account)
    if not profile:
        return None, None
    answer = await chat_completion(
        profile,
        prompt,
        log=log,
        temperature=temperature,
        timeout=timeout,
    )
    return answer.strip() if answer else None, profile.model
