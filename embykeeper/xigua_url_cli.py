import argparse
import asyncio
import sys

from loguru import logger

from embykeeper.config import config
from embykeeper.schema import TelegramAccount
from embykeeper.telegram.session import ClientsSession
from embykeeper.xigua_result import save_xigua_result

BOT_USERNAME = "XiguaEmbyBot"
PANEL_KEYWORDS = ("冰镇西瓜",)
BUTTON_KEYWORD = "签到"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="获取西瓜签到链接")
    parser.add_argument(
        "-c",
        "--config",
        default="config.toml",
        help="配置文件路径，默认使用当前目录的 config.toml",
    )
    parser.add_argument(
        "--phone",
        help="指定 Telegram 账号手机号，不填时使用第一个启用账号",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="主动拉取面板时的等待秒数，默认 15 秒",
    )
    return parser.parse_args(argv)


def configure_logging():
    logger.remove()
    logger.add(sys.stderr, level="ERROR")


def select_account(phone: str | None) -> TelegramAccount:
    accounts = [
        account for account in (config.telegram.account or []) if account.enabled and getattr(account, "checkiner", True)
    ]
    if not accounts:
        raise RuntimeError("配置中没有可用于签到的 Telegram 账号")

    if phone:
        phone = phone.replace(" ", "")
        for account in accounts:
            if account.phone == phone:
                return account
        raise RuntimeError(f"未找到手机号为 {phone} 的 Telegram 账号")

    return accounts[0]


def extract_raw_webapp_url(message) -> str | None:
    text = message.caption or message.text or ""
    if not message.reply_markup:
        return None
    if not any(keyword in text for keyword in PANEL_KEYWORDS):
        return None

    for row in message.reply_markup.inline_keyboard:
        for button in row:
            if BUTTON_KEYWORD in (button.text or "") and getattr(button, "web_app", None):
                return button.web_app.url
    return None


async def find_recent_raw_webapp_url(client, limit: int = 10) -> str | None:
    async for message in client.get_chat_history(BOT_USERNAME, limit=limit):
        url = extract_raw_webapp_url(message)
        if url:
            return url
    return None


async def wait_for_panel_after_start(client, timeout: float) -> str:
    sent = await client.send_message(BOT_USERNAME, "/start")
    deadline = asyncio.get_running_loop().time() + timeout

    while asyncio.get_running_loop().time() < deadline:
        async for message in client.get_chat_history(BOT_USERNAME, limit=10):
            if message.id <= sent.id:
                continue
            url = extract_raw_webapp_url(message)
            if url:
                return url
        await asyncio.sleep(1)

    raise RuntimeError("未能在限定时间内拿到西瓜签到面板")


async def build_signed_webview_url(client, raw_url: str) -> str:
    from pyrogram.raw.functions.messages import RequestWebView

    bot_peer = await client.resolve_peer(BOT_USERNAME)
    result = await client.invoke(
        RequestWebView(
            peer=bot_peer,
            bot=bot_peer,
            platform="ios",
            url=raw_url,
        )
    )
    return result.url


async def fetch_xigua_checkin_url_with_client(client, timeout: float = 15.0) -> str:
    raw_url = await find_recent_raw_webapp_url(client)
    if not raw_url:
        raw_url = await wait_for_panel_after_start(client, timeout)
    signed_url = await build_signed_webview_url(client, raw_url)
    save_xigua_result(url=signed_url)
    return signed_url


async def fetch_xigua_checkin_url(config_file: str, phone: str | None = None, timeout: float = 15.0) -> str:
    if not await config.reload_conf(config_file):
        raise RuntimeError(f"加载配置失败: {config_file}")

    return await fetch_xigua_checkin_url_from_config(phone=phone, timeout=timeout)


async def fetch_xigua_checkin_url_from_config(phone: str | None = None, timeout: float = 15.0) -> str:
    account = select_account(phone)

    async with ClientsSession([account]) as clients:
        async for _, client in clients:
            return await fetch_xigua_checkin_url_with_client(client, timeout=timeout)

    raise RuntimeError("Telegram 客户端初始化失败")


async def async_main(argv=None):
    args = parse_args(argv)
    configure_logging()
    signed_url = await fetch_xigua_checkin_url(args.config, phone=args.phone, timeout=args.timeout)
    print(signed_url)


def run(argv=None):
    try:
        asyncio.run(async_main(argv))
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        save_xigua_result(error=str(exc))
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    run()
