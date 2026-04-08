from __future__ import annotations

import asyncio
import re
from enum import IntEnum
from io import BytesIO
from typing import Optional, Union

from PIL import Image
from loguru import logger

from .client import chat_completion
from .profiles import resolve_profile

logger = logger.bind(scheme="ocr")


class CharRange(IntEnum):
    NUMBER = 0
    LLETTER = 1
    ULETTER = 2
    LLETTER_ULETTER = 3
    NUMBER_LLETTER = 4
    NUMBER_ULETTER = 5
    NUMBER_LLETTER_ULETTER = 6
    NOT_NUMBER_LLETTER_ULETTER = 7


def get_image_bytes(image_data: BytesIO) -> bytes:
    if isinstance(image_data, bytes):
        return image_data
    if isinstance(image_data, bytearray):
        return bytes(image_data)
    if hasattr(image_data, "getvalue"):
        return image_data.getvalue()
    if hasattr(image_data, "read"):
        if hasattr(image_data, "seek"):
            image_data.seek(0)
        return image_data.read()
    raise TypeError("不支持的图片数据类型")


def prepare_gif_for_ocr(gif_data: bytes) -> bytes:
    gif = Image.open(BytesIO(gif_data))
    frame_count = gif.n_frames
    num_frames = min(5, frame_count)
    if num_frames <= 1:
        gif.seek(0)
        frame = gif.convert("RGB")
        output = BytesIO()
        frame.save(output, format="PNG")
        return output.getvalue()

    frame_indices = [i * (frame_count - 1) // (num_frames - 1) for i in range(num_frames)]
    gif.seek(0)
    base_frame = gif.copy().convert("RGBA")
    composite = Image.new("RGBA", base_frame.size, (0, 0, 0, 0))
    alpha_per_frame = max(1, 255 // num_frames)

    for idx in frame_indices:
        gif.seek(idx)
        frame = gif.copy().convert("RGBA")
        frame.putalpha(alpha_per_frame)
        composite = Image.alpha_composite(composite, frame)

    output = BytesIO()
    composite.convert("RGB").save(output, format="PNG")
    return output.getvalue()


async def _get_photo_bytes(client, photo):
    if photo is None:
        return None
    if isinstance(photo, (bytes, bytearray)):
        return bytes(photo)
    if hasattr(photo, "getvalue"):
        return photo.getvalue()
    if hasattr(photo, "read"):
        if hasattr(photo, "seek"):
            photo.seek(0)
        return photo.read()
    data = await client.download_media(photo, in_memory=True)
    if data is None:
        return None
    return get_image_bytes(data)


async def solve_captcha(
    client,
    photo,
    expected_len: Union[int, list[int], tuple[int, ...], None] = None,
    timeout: int = 60,
    log=None,
):
    image_bytes = await _get_photo_bytes(client, photo)
    if not image_bytes:
        return None, None

    profile = resolve_profile("ocr", client)
    if not profile:
        return None, None

    prompt = profile.prompt or "识别图中验证码，并去除空格后仅返回验证码文本（字母或数字）"
    if expected_len:
        if isinstance(expected_len, int):
            prompt += f"\n验证码长度通常为 {expected_len}"
        else:
            prompt += f"\n验证码长度通常为 {'/'.join(str(v) for v in expected_len)}"

    text = await chat_completion(profile, prompt, image_bytes=image_bytes, log=log, timeout=timeout, temperature=0)
    normalized = re.sub(r"[^0-9A-Za-z]", "", (text or ""))
    return (normalized or text or "").strip(), profile.model


class OCRService:
    _pool = {}
    _pool_lock = asyncio.Lock()

    @classmethod
    async def get(
        cls,
        ocr_name: str = None,
        char_range: Optional[Union[CharRange, str]] = None,
    ):
        key = (ocr_name, char_range)
        async with cls._pool_lock:
            if key not in cls._pool:
                cls._pool[key] = cls(ocr_name, char_range)
            return cls._pool[key]

    def __init__(
        self,
        ocr_name: str = None,
        char_range: Optional[Union[CharRange, str]] = None,
    ) -> None:
        self.ocr_name = ocr_name
        self.char_range = char_range

    async def start(self):
        return

    async def stop(self, force: bool = False):
        return

    async def force_stop(self):
        return

    @classmethod
    def get_provider_name(cls) -> str:
        return "llm"

    @classmethod
    def get_provider_label(cls) -> str:
        return "本地 LLM OCR"

    @classmethod
    def using_remote_provider(cls) -> bool:
        return False

    async def run(self, image_data: BytesIO, timeout: int = 60, gif: bool = False) -> str:
        profile = resolve_profile("ocr")
        if not profile:
            raise RuntimeError("未配置 OCR 大模型, 请设置 llm.ocr")

        image_bytes = get_image_bytes(image_data)
        if gif:
            image_bytes = prepare_gif_for_ocr(image_bytes)
        prompt = profile.prompt or "识别图中验证码，并去除空格后仅返回验证码文本（字母或数字）"
        text = await chat_completion(profile, prompt, image_bytes=image_bytes, timeout=timeout, temperature=0)
        normalized = re.sub(r"[^0-9A-Za-z]", "", (text or ""))
        return normalized or text or ""

    def subscribe(self):
        return

    def unsubscribe(self):
        return

    def __enter__(self):
        self.subscribe()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unsubscribe()
        return False
