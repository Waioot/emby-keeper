from pyrogram.errors import RPCError
from pyrogram.types import Message

from embykeeper.llm.vision import choose_option

from . import AnswerBotCheckin


class TerminalCheckin(AnswerBotCheckin):
    name = "终点站 AI"
    # bot_username = "EmbyPublicBot"
    bot_username = "my_annunciator_boards_bot"
    bot_checkin_cmd = ["/checkin"]
    bot_text_ignore = ["会话已取消", "没有活跃的会话"]
    bot_checked_keywords = ["今天已签到"]
    required_capabilities = ["llm.vision"]
    max_retries = 1
    bot_use_history = 3

    async def on_photo(self, message: Message):
        """分析传入的验证码图片并点击匹配选项."""
        self.log.debug(f"{message.date} 收到验证码图片")

        if not message.reply_markup:
            return

        keys = [k for r in message.reply_markup.inline_keyboard for k in r]
        options = [k.text for k in keys]
        if len(options) < 2:
            return

        try:
            result, by = await choose_option(self.client, message, options, log=self.log)
            if not result:
                self.log.warning("签到失败: AI 识别错误.")
                return await self.fail()
            self.log.info(f"AI 解析答案 ({by}): {result}.")
            await message.click(result)
        except RPCError:
            self.log.warning("按钮点击失败.")
        except Exception as e:
            self.log.warning(f"签到失败: AI 识别错误 ({e.__class__.__name__}).")
            return await self.fail()
