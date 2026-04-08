from __future__ import annotations

import asyncio
from typing import Optional

from faker import Faker
from loguru import logger

from embykeeper.config import config
from embykeeper.utils import show_exception

logger = logger.bind(scheme="cfturnstile")


def is_solver_available() -> bool:
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except Exception:
        return False
    return True


def _build_playwright_proxy():
    proxy = getattr(config, "proxy", None)
    if not proxy:
        return None
    if not getattr(proxy, "hostname", None) or not getattr(proxy, "port", None):
        return None

    scheme = (getattr(proxy, "scheme", None) or "http").strip()
    proxy_data = {"server": f"{scheme}://{proxy.hostname}:{proxy.port}"}
    if getattr(proxy, "username", None):
        proxy_data["username"] = proxy.username
    if getattr(proxy, "password", None):
        proxy_data["password"] = proxy.password
    return proxy_data


async def solve_turnstile_token(url: str, timeout: float = 180.0, log=None) -> Optional[str]:
    log = log or logger
    if not is_solver_available():
        log.warning("当前未安装 playwright，无法进行本地 Turnstile 过盾。")
        return None

    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright

    proxy = _build_playwright_proxy()
    useragent = Faker().safari()
    deadline = asyncio.get_running_loop().time() + timeout

    browser = None
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, proxy=proxy)
            context = await browser.new_context(user_agent=useragent)
            page = await context.new_page()
            log.info("已启动本地浏览器会话，正在等待 Turnstile token。")
            await page.goto(url, wait_until="domcontentloaded", timeout=min(int(timeout * 1000), 45000))

            while asyncio.get_running_loop().time() < deadline:
                token = await page.evaluate(
                    """() => {
                        const selectors = [
                            "textarea[name='cf-turnstile-response']",
                            "input[name='cf-turnstile-response']",
                        ];
                        for (const selector of selectors) {
                            const node = document.querySelector(selector);
                            if (node && typeof node.value === "string" && node.value.trim()) {
                                return node.value.trim();
                            }
                        }
                        return "";
                    }"""
                )
                if token:
                    return token
                await asyncio.sleep(1)
    except PlaywrightTimeoutError:
        log.warning("本地 Turnstile 页面加载超时，未获得 token。")
    except Exception as e:
        log.warning("本地 Turnstile 解析失败。")
        show_exception(e, regular=False)
    finally:
        if browser:
            await browser.close()
    return None
