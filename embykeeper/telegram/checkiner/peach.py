import asyncio
import random
from pyrogram.types import Message

from embykeeper.utils import to_iterable

from . import BotCheckin, MessageType
from ._base import default_keywords


class PeachCheckin(BotCheckin):
    name = "Peach"
    bot_username = "peach_emby_bot"
    bot_checkin_cmd = "/start"
    bot_captcha_len = 4
    bot_checkin_caption_pat = "请输入验证码"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._message_lock = asyncio.Lock()
        self._retry_pending = False
        self._handled_message_signatures = {}

    def _get_message_signature(self, message: Message) -> str:
        text = message.text or message.caption or ""
        buttons = []
        if message.reply_markup and getattr(message.reply_markup, "inline_keyboard", None):
            buttons = [k.text for r in message.reply_markup.inline_keyboard for k in r]
        return "|".join([text, "||".join(buttons)])

    async def message_handler(self, client, message: Message):
        async with self._message_lock:
            if self.finished.is_set():
                return

            type = self.message_type(message)
            text = message.text or message.caption or ""
            is_welcome = bool(message.caption and "欢迎使用" in message.caption and message.reply_markup)
            signature = self._get_message_signature(message)

            if self._handled_message_signatures.get(message.id) == signature:
                self.log.debug("[gray50]忽略重复消息更新.[/]")
                return

            if self._retry_pending and not is_welcome:
                fail_keywords = to_iterable(self.bot_fail_keywords) or default_keywords["fail"]
                if text and any(s in text for s in fail_keywords):
                    self.log.debug("[gray50]忽略上一轮重复失败消息.[/]")
                else:
                    self.log.debug("[gray50]等待下一轮欢迎页面, 忽略旧消息.[/]")
                return

            if is_welcome:
                self._retry_pending = False
                self._handled_message_signatures[message.id] = signature
                keys = [k.text for r in message.reply_markup.inline_keyboard for k in r]
                for k in keys:
                    if "签到" in k:
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        await message.click(k)
                        return
                else:
                    self.log.warning("签到失败: 账户错误.")
                    return await self.fail()

            if MessageType.CAPTCHA in type:
                self._handled_message_signatures[message.id] = signature

            await super().message_handler(client, message, type=type)
            self._handled_message_signatures[message.id] = signature

    async def retry(self):
        if self.finished.is_set():
            return
        if self._retry_pending:
            self.log.debug("[gray50]已有待处理重试, 忽略重复重试请求.[/]")
            return
        self._retry_pending = True
        await super().retry()
