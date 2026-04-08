import asyncio
from pathlib import Path

import tomli as tomllib
from loguru import logger

from embykeeper.cli import AsyncTyper
from embykeeper.notify import start_notifier
from embykeeper.config import config
from embykeeper.notifier.telegram_bot import resolve_bot_token, resolve_chat_id, send_message

app = AsyncTyper()


@app.async_command()
async def log(config_file: Path):
    await config.reload_conf(config_file)
    await start_notifier()
    logger.bind(log=True).info("Test logging.")


@app.async_command()
async def disconnect(config_file: Path):
    await config.reload_conf(config_file)
    bot_token = resolve_bot_token()
    chat_id = resolve_chat_id()
    if not bot_token or chat_id is None:
        raise RuntimeError("未配置可用的 Telegram Bot 推送参数")
    print("Sending Test1")
    await send_message(bot_token, chat_id, "ERROR#Test1")
    print("Wait for 40 seconds")
    await asyncio.sleep(40)
    print("Sending Test2")
    await send_message(bot_token, chat_id, "ERROR#Test2")
    print("Sent Test2")


if __name__ == "__main__":
    app()
