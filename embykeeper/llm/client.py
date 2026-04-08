from __future__ import annotations

import base64
import json
from typing import Optional

import httpx

from embykeeper.config import config
from embykeeper.utils import get_proxy_str

from .profiles import ResolvedLLMProfile


def detect_image_mime(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def extract_text_from_response(data: dict) -> str:
    choices = data.get("choices", [])
    if not choices:
        return ""

    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text" and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
            elif isinstance(part.get("content"), str):
                text_parts.append(part["content"])
        return "\n".join(text_parts).strip()

    return ""


def _build_content(prompt: str, image_bytes: bytes | None = None, image_detail: Optional[str] = None):
    content = [{"type": "text", "text": prompt}]
    if image_bytes:
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        image_url = {
            "url": f"data:{detect_image_mime(image_bytes)};base64,{image_base64}",
        }
        if image_detail:
            image_url["detail"] = image_detail
        content.append({"type": "image_url", "image_url": image_url})
    return content


async def chat_completion(
    profile: ResolvedLLMProfile,
    prompt: str,
    image_bytes: bytes | None = None,
    log=None,
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
    image_detail: Optional[str] = None,
) -> str:
    if not all((profile.base_url, profile.model, profile.api_key)):
        raise RuntimeError("LLM 配置不完整")

    payload = {
        "model": profile.model,
        "messages": [{"role": "user", "content": _build_content(prompt, image_bytes, image_detail or profile.image_detail)}],
        "stream": False,
    }
    if temperature is None:
        temperature = profile.temperature
    if temperature is not None:
        payload["temperature"] = temperature

    request_timeout = timeout or profile.timeout
    proxy = get_proxy_str(config.proxy) if getattr(config, "proxy", None) else None
    url = profile.base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {profile.api_key}",
        "Content-Type": "application/json",
    }

    last_error = None
    for attempt in range(max(profile.retries, 1)):
        try:
            async with httpx.AsyncClient(
                http2=True,
                proxy=proxy,
                timeout=request_timeout,
                follow_redirects=True,
            ) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                text = extract_text_from_response(data).strip()
                if text:
                    return text
                return json.dumps(data, ensure_ascii=False, indent=2)
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            last_error = RuntimeError(f"HTTP error {exc.response.status_code}: {body}")
        except (httpx.HTTPError, ValueError) as exc:
            last_error = RuntimeError(f"Request failed: {exc}")

        if log and attempt + 1 < max(profile.retries, 1):
            log.warning(f"LLM 请求失败, 正在重试 ({attempt + 1}/{profile.retries}).")

    if last_error:
        raise last_error
    raise RuntimeError("LLM 请求失败")


async def call_openai_compatible_chat(
    prompt: str,
    base_url: str,
    model: str,
    api_key: str,
    image_bytes: bytes | None = None,
    timeout: Optional[float] = None,
    retries: int = 3,
    temperature: Optional[float] = None,
    image_detail: Optional[str] = None,
    log=None,
) -> str:
    profile = ResolvedLLMProfile(
        name="custom",
        base_url=base_url,
        model=model,
        api_key=api_key,
        prompt=None,
        timeout=timeout or 60.0,
        retries=retries,
        temperature=temperature,
        image_detail=image_detail or "high",
        account=None,
    )
    return await chat_completion(
        profile,
        prompt=prompt,
        image_bytes=image_bytes,
        log=log,
        temperature=temperature,
        timeout=timeout,
        image_detail=image_detail,
    )
