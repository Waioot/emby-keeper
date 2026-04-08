from pyrogram.types import Message

from embykeeper.var import console

from . import Monitor

__ignore__ = True


class TerminusExamMonitor(Monitor):
    name = "终点站考试辅助"
    chat_name = "EmbyPublicBot"
    chat_keyword = r"(.*?(?:\n(?!本题贡献者).*?)*)\s+本题贡献者"
    allow_edit = True
    unsupported_reason = "终点站考试辅助依赖已移除的远程答题服务，当前阶段已跳过。"
    debug_no_log = True
    trigger_interval = 0
    trigger_sem = None

    async def init(self):
        return True

    async def on_trigger(self, message: Message, key, reply):
        console.rule(title="终点站考试辅助已停用")
        console.print("当前阶段不再访问远程答题服务，请手动作答。")
        console.rule()
