from __future__ import annotations

import asyncio
import io
import os
from contextlib import suppress
from typing import Any, Optional

import httpx
from loguru import logger
from rich.text import Text

from embykeeper.config import config
from embykeeper.utils import get_proxy_str, show_exception

logger = logger.bind(scheme="telegrambot", nonotify=True)

TELEGRAM_MESSAGE_LIMIT = 3900
DEFAULT_TIMEOUT = 20.0


def _strip_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def resolve_bot_token() -> Optional[str]:
    candidates = []
    bot = getattr(config, "bot", None)
    if bot is not None:
        candidates.append(getattr(bot, "token", None))

    notifier = getattr(config, "notifier", None)
    if notifier is not None:
        telegram_bot = getattr(notifier, "telegram_bot", None)
        if telegram_bot is not None:
            candidates.append(getattr(telegram_bot, "bot_token", None))

    candidates.extend(
        [
            os.getenv("EMBYKEEPER_BOT_TOKEN"),
            os.getenv("TELEGRAM_BOT_TOKEN"),
            os.getenv("BOT_TOKEN"),
        ]
    )
    for value in candidates:
        token = _strip_text(value)
        if token:
            return token
    return None


def resolve_chat_id() -> Any:
    notifier = getattr(config, "notifier", None)
    candidates = []
    if notifier is not None:
        telegram_bot = getattr(notifier, "telegram_bot", None)
        if telegram_bot is not None:
            candidates.append(getattr(telegram_bot, "chat_id", None))

    bot = getattr(config, "bot", None)
    if bot is not None:
        candidates.append(getattr(bot, "chat_id", None))

    candidates.extend(
        [
            os.getenv("EMBYKEEPER_BOT_CHAT_ID"),
            os.getenv("TELEGRAM_BOT_CHAT_ID"),
            os.getenv("CHAT_ID"),
        ]
    )

    for value in candidates:
        if value is None:
            continue
        if isinstance(value, str):
            token = value.strip()
            if token:
                if token.isdigit() or (token.startswith("-") and token[1:].isdigit()) or token.startswith("@"):
                    return token
                return token
        else:
            return value
    return None


class TelegramBotClient:
    def __init__(self, bot_token: str, timeout: float = DEFAULT_TIMEOUT):
        self.bot_token = bot_token
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        proxy = None
        if getattr(config, "proxy", None):
            proxy = get_proxy_str(config.proxy)
        self._client = httpx.AsyncClient(
            http2=True,
            timeout=self.timeout,
            proxy=proxy,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()
        return False

    async def aclose(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _api_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    async def _post(self, method: str, data: dict, files: dict | None = None):
        if self._client is None:
            raise RuntimeError("Telegram Bot 客户端尚未初始化")
        try:
            response = await self._client.post(self._api_url(method), data=data, files=files)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Telegram Bot API 请求失败: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError("Telegram Bot API 返回了非法 JSON") from exc

        if not payload.get("ok", False):
            description = payload.get("description") or "未知错误"
            raise RuntimeError(f"Telegram Bot API 调用失败: {description}")
        return payload.get("result")

    async def send_message(
        self,
        chat_id: Any,
        text: str,
        disable_web_page_preview: bool = True,
    ):
        data = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true" if disable_web_page_preview else "false",
        }
        return await self._post("sendMessage", data=data)

    async def send_document(
        self,
        chat_id: Any,
        text: str,
        filename: str = "message.txt",
        caption: Optional[str] = None,
    ):
        content = text.encode("utf-8")
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        files = {"document": (filename, content, "text/plain; charset=utf-8")}
        return await self._post("sendDocument", data=data, files=files)


async def send_message(bot_token: str, chat_id: Any, text: str):
    async with TelegramBotClient(bot_token) as client:
        return await client.send_message(chat_id, text)


async def send_document(bot_token: str, chat_id: Any, text: str, filename: str = "message.txt"):
    async with TelegramBotClient(bot_token) as client:
        return await client.send_document(chat_id, text, filename=filename)


class TelegramBotStream(io.TextIOBase):
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Any = None,
        document_mode: bool = False,
        prefer_document: bool = True,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        super().__init__()
        self.bot_token = bot_token or resolve_bot_token()
        self.chat_id = chat_id if chat_id is not None else resolve_chat_id()
        self.document_mode = document_mode
        self.prefer_document = prefer_document
        self.timeout = timeout
        self.queue = asyncio.Queue()
        self._loop = asyncio.get_running_loop()
        self._watch = asyncio.create_task(self.watchdog())

    def close(self):
        return None

    def _enqueue(self, message: str):
        if not message:
            return
        if self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(self.queue.put_nowait, message)

    async def watchdog(self):
        if not self.bot_token:
            logger.error("Telegram Bot Token 未配置, 无法发送日志通知.")
            return
        if self.chat_id is None:
            logger.error("Telegram Bot 目标 chat_id 未配置, 无法发送日志通知.")
            return

        async with TelegramBotClient(self.bot_token, timeout=self.timeout) as client:
            while True:
                message = await self.queue.get()
                try:
                    await asyncio.wait_for(self._send(client, message), self.timeout)
                except asyncio.CancelledError:
                    raise
                except asyncio.TimeoutError:
                    logger.warning("推送消息到 Telegram Bot 超时.")
                except Exception as e:
                    logger.warning("推送消息到 Telegram Bot 失败.")
                    show_exception(e)
                finally:
                    self.queue.task_done()

    async def _send(self, client: TelegramBotClient, message: str):
        if self.document_mode:
            caption = message[:200] if message else None
            if caption and len(caption) == len(message):
                caption = None
            return await client.send_document(self.chat_id, message, caption=caption)

        if self.prefer_document and (len(message) > TELEGRAM_MESSAGE_LIMIT or "\n" in message):
            caption = message[:200] if message else None
            if caption and len(caption) == len(message):
                caption = None
            return await client.send_document(self.chat_id, message, caption=caption)

        return await client.send_message(self.chat_id, message)

    def write(self, message):
        message = Text.from_markup(message).plain
        if message.endswith("\n"):
            message = message[:-1]
        if message:
            self._enqueue(message)
        return len(message)

    async def join(self):
        await self.queue.join()
        self._watch.cancel()
        with suppress(asyncio.CancelledError):
            await self._watch
