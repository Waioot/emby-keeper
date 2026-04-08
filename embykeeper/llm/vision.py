from __future__ import annotations

import string
from typing import Optional

from thefuzz import process

from embykeeper.utils import truncate_str

from .client import chat_completion
from .ocr import _get_photo_bytes
from .profiles import resolve_profile


def normalize_ai_answer(text: str) -> str:
    if not text:
        return ""
    punctuation = string.punctuation + "，。！？；：、“”‘’（）【】《》〈〉「」『』"
    normalized = text.translate(str.maketrans("", "", punctuation))
    return "".join(normalized.split()).strip().lower()


def match_option(answer: str, options: list[str]) -> Optional[str]:
    normalized_answer = normalize_ai_answer(answer)
    if not normalized_answer:
        return None

    normalized_options = {normalize_ai_answer(option): option for option in options}
    if normalized_answer in normalized_options:
        return normalized_options[normalized_answer]

    for normalized_option, option in normalized_options.items():
        if normalized_option and (
            normalized_option in normalized_answer or normalized_answer in normalized_option
        ):
            return option

    matched = process.extractOne(normalized_answer, list(normalized_options.keys()))
    if matched and matched[1] >= 60:
        return normalized_options[matched[0]]
    return None


async def choose_option(client, photo, options: list[str], question: str | None = None, log=None, timeout: int = 60):
    image_bytes = await _get_photo_bytes(client, photo)
    if not image_bytes:
        return None, None

    profile = resolve_profile("vision", client)
    if not profile:
        return None, None

    prompt = [
        "你在处理 Telegram 签到图片选择题。",
        "请观察图片内容，从候选项中选出最匹配的一项。",
        "只返回一个候选项原文，不要解释，不要添加任何其他文字。",
        f"候选项: {' / '.join(options)}",
    ]
    if question:
        prompt.insert(1, f"补充问题: {question}")

    answer = await chat_completion(profile, "\n".join(prompt), image_bytes=image_bytes, log=log, timeout=timeout)
    matched = match_option(answer, options)
    if not matched and log:
        log.warning(f'视觉问题解答失败: 大模型返回 "{truncate_str(answer, 40)}", 无法匹配候选项.')
    return matched, profile.model
