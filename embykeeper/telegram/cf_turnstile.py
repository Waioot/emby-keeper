from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import subprocess
import sys
from typing import Optional, Sequence
from urllib.parse import urlparse

from loguru import logger

from embykeeper.config import config
from embykeeper.utils import show_exception, truncate_str

logger = logger.bind(scheme="cfturnstile")

_CHROME_VERSION = "135"
_CHROME_FULL_VERSION = "135.0.0.0"
_CHROME_BRANDS = [
    {"brand": "Google Chrome", "version": _CHROME_VERSION},
    {"brand": "Chromium", "version": _CHROME_VERSION},
    {"brand": "Not.A/Brand", "version": "99"},
]
_CHROME_FULL_BRANDS = [
    {"brand": "Google Chrome", "version": _CHROME_FULL_VERSION},
    {"brand": "Chromium", "version": _CHROME_FULL_VERSION},
    {"brand": "Not.A/Brand", "version": "99.0.0.0"},
]

_SOLVER_DIAGNOSIS: Optional[tuple[bool, Optional[str]]] = None
_MANAGED_CHECKIN_SUCCESS_KEYWORDS = ("签到成功", "签到完成", "领取成功", "已完成签到")
_MANAGED_CHECKIN_CHECKED_KEYWORDS = ("今日已签到", "已经签到", "已签到", "重复签到", "请明天再来")
_MANAGED_CHECKIN_FAIL_KEYWORDS = ("签到失败", "领取失败", "操作失败", "请稍后重试")
_MANAGED_RESPONSE_PATH_KEYWORDS = ("checkin", "signin", "sign-in", "reward", "claim")
_TURNSTILE_VALIDATION_FAIL_KEYWORDS = ("turnstile验证失败", "cloudflareturnstile验证失败")
_TURNSTILE_CHALLENGE_CLICK_FACTORS = (
    (0.093, 0.50),
    (0.060, 0.50),
    (0.140, 0.50),
    (0.093, 0.31),
    (0.093, 0.68),
)


@dataclass
class TurnstileManagedResult:
    status: str
    detail: Optional[str] = None


def _normalize_launch_error(message: str) -> str:
    message = (message or "").strip()
    lowered = message.lower()
    if "no module named 'playwright'" in lowered:
        return "未安装 playwright Python 包"
    if "executable doesn't exist" in lowered or "please run the following command to download new browsers" in lowered:
        return "未安装 Chromium 浏览器资源, 请先执行 python -m playwright install chromium"
    if message:
        return f"Chromium 启动失败: {message}"
    return "Chromium 启动失败"


def diagnose_solver() -> tuple[bool, Optional[str]]:
    global _SOLVER_DIAGNOSIS
    if _SOLVER_DIAGNOSIS is not None:
        return _SOLVER_DIAGNOSIS

    try:
        import playwright.async_api  # noqa: F401
    except Exception:
        _SOLVER_DIAGNOSIS = (False, "未安装 playwright Python 包")
        return _SOLVER_DIAGNOSIS

    probe = """
import json

try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    print(json.dumps({"available": False, "reason": str(e)}))
    raise SystemExit(0)

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        browser.close()
except Exception as e:
    print(json.dumps({"available": False, "reason": str(e)}))
else:
    print(json.dumps({"available": True, "reason": None}))
""".strip()

    try:
        proc = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except Exception as e:
        _SOLVER_DIAGNOSIS = (False, f"无法检测 Chromium 运行环境: {e}")
        return _SOLVER_DIAGNOSIS

    output = (proc.stdout or "").strip().splitlines()
    if output:
        try:
            result = json.loads(output[-1])
        except json.JSONDecodeError:
            result = None
        if isinstance(result, dict):
            available = bool(result.get("available"))
            reason = result.get("reason")
            _SOLVER_DIAGNOSIS = (available, None if available else _normalize_launch_error(reason))
            return _SOLVER_DIAGNOSIS

    stderr = (proc.stderr or "").strip()
    _SOLVER_DIAGNOSIS = (False, _normalize_launch_error(stderr or "无法检测 Chromium 运行环境"))
    return _SOLVER_DIAGNOSIS


def is_solver_available() -> bool:
    available, _ = diagnose_solver()
    return available


def get_solver_unavailable_reason() -> Optional[str]:
    available, reason = diagnose_solver()
    return None if available else reason


def _build_playwright_proxy():
    try:
        proxy = getattr(config, "proxy", None)
    except RuntimeError:
        return None
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


def _build_playwright_launch_kwargs(proxy=None):
    launch_kwargs = {
        "headless": True,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--window-size=1440,900",
        ],
    }
    if proxy:
        launch_kwargs["proxy"] = proxy
    return launch_kwargs


async def _apply_stealth_context(context):
    await context.add_init_script(
        f"""() => {{
            const override = (obj, key, value) => {{
                try {{
                    Object.defineProperty(obj, key, {{ get: () => value, configurable: true }});
                }} catch (e) {{}}
            }};

            const overrideMethod = (obj, key, value) => {{
                try {{
                    Object.defineProperty(obj, key, {{ value, configurable: true }});
                }} catch (e) {{}}
            }};

            override(navigator, 'webdriver', undefined);
            override(navigator, 'platform', 'MacIntel');
            override(navigator, 'vendor', 'Google Inc.');
            override(navigator, 'languages', ['zh-CN', 'zh', 'en-US', 'en']);
            override(navigator, 'language', 'zh-CN');
            override(navigator, 'plugins', [1, 2, 3, 4, 5]);
            override(navigator, 'hardwareConcurrency', 8);
            override(navigator, 'deviceMemory', 8);
            override(navigator, 'maxTouchPoints', 0);
            override(screen, 'availWidth', 1440);
            override(screen, 'availHeight', 900);
            override(screen, 'width', 1440);
            override(screen, 'height', 900);
            override(window, 'devicePixelRatio', 1);

            if (!window.chrome) {{
                window.chrome = {{ runtime: {{}}, app: {{}} }};
            }} else {{
                if (!window.chrome.runtime) window.chrome.runtime = {{}};
                if (!window.chrome.app) window.chrome.app = {{}};
            }}

            overrideMethod(navigator, 'pdfViewerEnabled', true);

            if (navigator.permissions && navigator.permissions.query) {{
                const originalQuery = navigator.permissions.query.bind(navigator.permissions);
                navigator.permissions.query = (parameters) => {{
                    if (parameters && parameters.name === 'notifications') {{
                        return Promise.resolve({{ state: Notification.permission }});
                    }}
                    return originalQuery(parameters);
                }};
            }}

            const brands = {json.dumps(_CHROME_BRANDS, ensure_ascii=False)};
            const fullVersionList = {json.dumps(_CHROME_FULL_BRANDS, ensure_ascii=False)};
            override(navigator, 'userAgentData', {{
                brands,
                mobile: false,
                platform: 'macOS',
                getHighEntropyValues: async (hints) => {{
                    const values = {{
                        brands,
                        mobile: false,
                        platform: 'macOS',
                        platformVersion: '14.0.0',
                        architecture: 'x86',
                        bitness: '64',
                        model: '',
                        uaFullVersion: '{_CHROME_FULL_VERSION}',
                        fullVersionList,
                        wow64: false,
                    }};
                    if (!Array.isArray(hints)) {{
                        return values;
                    }}
                    return Object.fromEntries(hints.filter((hint) => hint in values).map((hint) => [hint, values[hint]]));
                }},
                toJSON: () => ({{ brands, mobile: false, platform: 'macOS' }}),
            }});

            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, parameter);
            }};
            if (window.WebGL2RenderingContext) {{
                const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) return 'Intel Inc.';
                    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                    return getParameter2.call(this, parameter);
                }};
            }};
        }}"""
    )


def _build_playwright_useragent() -> str:
    return (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{_CHROME_FULL_VERSION} Safari/537.36"
    )


def _build_playwright_context_kwargs(useragent: str) -> dict:
    return {
        "user_agent": useragent,
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
        "viewport": {"width": 1440, "height": 900},
        "screen": {"width": 1440, "height": 900},
        "device_scale_factor": 1,
        "has_touch": False,
        "is_mobile": False,
        "color_scheme": "light",
    }


async def _extract_turnstile_token(page) -> str:
    return await page.evaluate(
        """() => {
            const selectors = [
                "textarea[name='cf-turnstile-response']",
                "input[name='cf-turnstile-response']",
                "textarea[name='g-recaptcha-response']",
                "input[name='g-recaptcha-response']",
                "#cf-turnstile-response",
                "#g-recaptcha-response",
            ];
            for (const selector of selectors) {
                const nodes = document.querySelectorAll(selector);
                for (const node of nodes) {
                    if (node && typeof node.value === "string" && node.value.trim()) {
                        return node.value.trim();
                    }
                }
            }
            const allFields = document.querySelectorAll("textarea, input");
            for (const node of allFields) {
                const name = (node.getAttribute("name") || "").toLowerCase();
                const id = (node.getAttribute("id") || "").toLowerCase();
                const value = typeof node.value === "string" ? node.value.trim() : "";
                if (!value) continue;
                if (
                    name.includes("turnstile") ||
                    name.includes("captcha") ||
                    id.includes("turnstile") ||
                    id.includes("captcha")
                ) {
                    return value;
                }
            }
            return "";
        }"""
    )


async def _describe_turnstile_page(page) -> dict:
    return await page.evaluate(
        """() => {
            const fields = Array.from(document.querySelectorAll("textarea, input")).map((node) => ({
                tag: node.tagName,
                type: node.getAttribute("type") || "",
                name: node.getAttribute("name") || "",
                id: node.getAttribute("id") || "",
                valueLength: typeof node.value === "string" ? node.value.trim().length : 0,
            }));
            const widgets = Array.from(document.querySelectorAll("iframe, [data-sitekey], .cf-turnstile")).map((node) => ({
                tag: node.tagName,
                src: node.getAttribute("src") || "",
                className: node.getAttribute("class") || "",
                sitekey: node.getAttribute("data-sitekey") || "",
                id: node.getAttribute("id") || "",
            }));
            const actionCandidates = Array.from(
                document.querySelectorAll(
                    "button, a, [role='button'], input[type='button'], input[type='submit']"
                )
            )
                .map((node) => {
                    const text = (
                        node.innerText ||
                        node.textContent ||
                        node.getAttribute("value") ||
                        node.getAttribute("aria-label") ||
                        ""
                    ).trim();
                    const rect = node.getBoundingClientRect();
                    return {
                        tag: node.tagName,
                        type: node.getAttribute("type") || "",
                        text,
                        className: node.getAttribute("class") || "",
                        id: node.getAttribute("id") || "",
                        disabled:
                            !!node.disabled ||
                            node.getAttribute("aria-disabled") === "true" ||
                            node.classList.contains("disabled"),
                        visible: rect.width > 0 && rect.height > 0,
                        backgroundColor: getComputedStyle(node).backgroundColor,
                        color: getComputedStyle(node).color,
                    };
                })
                .filter((node) => node.text && node.visible && node.text.includes("签到"))
                .slice(0, 10);
            const successTexts = ["成功", "验证完成", "cloudflare turnstile 验证完成"];
            const loweredBody = (document.body && document.body.innerText ? document.body.innerText : "").toLowerCase();
            const hasSuccessText = successTexts.some((text) => loweredBody.includes(text));
            return {
                url: location.href,
                title: document.title || "",
                readyState: document.readyState,
                fieldCount: fields.length,
                fields,
                widgets,
                actionCandidates,
                hasSuccessText,
                bodyText: (document.body && document.body.innerText ? document.body.innerText : "").slice(0, 500),
            };
        }"""
    )


async def _advance_turnstile_page(page, action_texts: Sequence[str] = ("签到",)) -> tuple[bool, str | None]:
    candidates = await _describe_turnstile_page(page)
    for target_text in _get_turnstile_action_targets(candidates, action_texts):
        clicked = await _click_turnstile_action(page, target_text)
        if clicked:
            return True, target_text
    return False, None


def _get_turnstile_action_targets(candidates: dict, action_texts: Sequence[str] = ("签到",)) -> list[str]:
    actions = candidates.get("actionCandidates") or []
    normalized_targets = [text.strip().lower() for text in action_texts if text and text.strip()]
    preferred = []
    fallback = []
    for candidate in actions:
        text = (candidate.get("text") or "").strip()
        if not text or candidate.get("disabled"):
            continue
        normalized = text.lower()
        if "成功" in text or "验证完成" in text:
            continue
        if any(normalized == target for target in normalized_targets):
            preferred.append(text)
        elif any(target in normalized for target in normalized_targets):
            fallback.append(text)
    return preferred + fallback


async def _click_turnstile_action(page, target_text: str) -> bool:
    return await page.evaluate(
        """(targetText) => {
            const selectors = [
                "button",
                "a",
                "[role='button']",
                "input[type='button']",
                "input[type='submit']",
            ];
            for (const selector of selectors) {
                for (const node of document.querySelectorAll(selector)) {
                    const text = (
                        node.innerText ||
                        node.textContent ||
                        node.getAttribute('value') ||
                        node.getAttribute('aria-label') ||
                        ''
                    ).trim();
                    if (text !== targetText) continue;
                    if (node.disabled || node.getAttribute('aria-disabled') === 'true' || node.classList.contains('disabled')) {
                        return false;
                    }
                    node.click();
                    return true;
                }
            }
            return false;
        }""",
        target_text,
    )


def _normalize_turnstile_text(text: str) -> str:
    return "".join((text or "").strip().lower().split())


def _format_turnstile_detail(text: str | None, limit: int = 160) -> str | None:
    if not text:
        return None
    return truncate_str(" ".join(text.split()), limit)


def _summarize_turnstile_actions(actions: Sequence[dict] | None) -> str:
    parts = []
    for action in actions or []:
        text = (action.get("text") or "").strip()
        if not text:
            continue
        parts.append(f"{text}(disabled={bool(action.get('disabled'))})")
    return ", ".join(parts[:6]) if parts else "-"


def _classify_turnstile_validation_text(text: str | None) -> TurnstileManagedResult | None:
    normalized = _normalize_turnstile_text(text)
    if not normalized:
        return None
    if any(keyword in normalized for keyword in _TURNSTILE_VALIDATION_FAIL_KEYWORDS):
        return TurnstileManagedResult("fail", _format_turnstile_detail(text))
    return None


def _is_turnstile_challenge_frame_url(url: str | None) -> bool:
    normalized = (url or "").strip().lower()
    return normalized.startswith("https://challenges.cloudflare.com/") and "turnstile" in normalized


def _build_turnstile_checkbox_point(box: dict, attempt: int) -> tuple[float, float]:
    width = max(float(box.get("width") or 0), 1.0)
    height = max(float(box.get("height") or 0), 1.0)
    fx, fy = _TURNSTILE_CHALLENGE_CLICK_FACTORS[attempt % len(_TURNSTILE_CHALLENGE_CLICK_FACTORS)]
    x = min(width - 8, max(8, width * fx))
    y = min(height - 8, max(8, height * fy))
    return x, y


async def _try_click_turnstile_challenge(page, *, attempt: int = 0) -> tuple[bool, str | None]:
    for frame in page.frames:
        if not _is_turnstile_challenge_frame_url(frame.url):
            continue
        try:
            element = await frame.frame_element()
            box = await element.bounding_box()
        except Exception:
            continue
        if not box:
            continue

        local_x, local_y = _build_turnstile_checkbox_point(box, attempt)
        abs_x = box["x"] + local_x
        abs_y = box["y"] + local_y
        await page.mouse.move(max(abs_x - 20, box["x"] + 4), abs_y, steps=6)
        await page.mouse.move(abs_x, abs_y, steps=8)
        await page.mouse.click(abs_x, abs_y, delay=120)
        return True, f"{int(local_x)},{int(local_y)}"
    return False, None


def _classify_managed_checkin_text(
    text: str | None, *, treat_checked_as_success: bool = False
) -> TurnstileManagedResult | None:
    normalized = _normalize_turnstile_text(text)
    if not normalized:
        return None

    for keyword in _MANAGED_CHECKIN_FAIL_KEYWORDS:
        if _normalize_turnstile_text(keyword) in normalized:
            return TurnstileManagedResult("fail", _format_turnstile_detail(text))

    for keyword in _MANAGED_CHECKIN_SUCCESS_KEYWORDS:
        if _normalize_turnstile_text(keyword) in normalized:
            return TurnstileManagedResult("success", _format_turnstile_detail(text))

    for keyword in _MANAGED_CHECKIN_CHECKED_KEYWORDS:
        if _normalize_turnstile_text(keyword) in normalized:
            status = "success" if treat_checked_as_success else "checked"
            return TurnstileManagedResult(status, _format_turnstile_detail(text))

    return None


def _is_candidate_managed_response(response, origin: str) -> bool:
    url = (response.url or "").lower()
    if not url.startswith(origin.lower()) or "challenges.cloudflare.com" in url:
        return False

    request = response.request
    if request.method == "OPTIONS":
        return False

    path = urlparse(response.url).path.lower()
    return any(keyword in path for keyword in _MANAGED_RESPONSE_PATH_KEYWORDS)


async def _classify_managed_response(response) -> TurnstileManagedResult:
    body = None
    try:
        body = await response.text()
    except Exception:
        body = None

    classified = _classify_managed_checkin_text(body)
    if classified:
        return classified

    detail = _format_turnstile_detail(body) or f"接口返回状态码 {response.status}"
    if response.status == 409:
        return TurnstileManagedResult("checked", detail)
    if 200 <= response.status < 300:
        return TurnstileManagedResult("success", detail)
    return TurnstileManagedResult("fail", detail)


async def solve_turnstile_managed(
    url: str,
    action_texts: Sequence[str] = ("签到",),
    timeout: float = 180.0,
    log=None,
) -> TurnstileManagedResult:
    log = log or logger
    available, reason = diagnose_solver()
    if not available:
        detail = f"当前无法进行本地 Turnstile 过盾: {reason}."
        log.warning(detail)
        return TurnstileManagedResult("fail", detail)

    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright

    proxy = _build_playwright_proxy()
    useragent = _build_playwright_useragent()
    deadline = asyncio.get_running_loop().time() + timeout
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    browser = None
    try:
        async with async_playwright() as pw:
            log.info(
                f"已启动本地 Turnstile 检测, 正在打开验证页面 ({'使用代理' if proxy else '直连'})."
            )
            browser = await pw.chromium.launch(**_build_playwright_launch_kwargs(proxy))
            context = await browser.new_context(**_build_playwright_context_kwargs(useragent))
            await _apply_stealth_context(context)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=min(int(timeout * 1000), 45000))
            log.debug("Turnstile 托管页面已完成初始加载, 开始等待自动验证并执行页面操作.")

            diagnosed = False
            clicked_action = False
            challenge_attempts = 0
            last_challenge_click_at = 0.0
            while asyncio.get_running_loop().time() < deadline:
                now = asyncio.get_running_loop().time()
                token = await _extract_turnstile_token(page)
                snapshot = await _describe_turnstile_page(page)
                body_text = snapshot.get("bodyText") or ""
                widget_count = len(snapshot.get("widgets") or [])
                actions = snapshot.get("actionCandidates") or []
                targets = _get_turnstile_action_targets(snapshot, action_texts)
                turnstile_failed = _classify_turnstile_validation_text(body_text)

                if not diagnosed:
                    diagnosed = True
                    log.debug(
                        f"托管页面状态: title={snapshot.get('title') or '-'}, readyState={snapshot.get('readyState')}, "
                        f"widgets={widget_count}, actions={_summarize_turnstile_actions(actions)}, "
                        f"body={truncate_str(body_text, 160)}"
                    )

                if turnstile_failed:
                    detail = turnstile_failed.detail or "Cloudflare Turnstile 验证失败"
                    log.warning(f"检测到 Turnstile 验证失败状态: {detail}.")
                    return TurnstileManagedResult("fail", detail)

                if clicked_action:
                    classified = _classify_managed_checkin_text(body_text, treat_checked_as_success=True)
                    if classified:
                        return classified
                    await asyncio.sleep(1)
                    continue

                challenge_present = any(_is_turnstile_challenge_frame_url(frame.url) for frame in page.frames)
                if challenge_present and now - last_challenge_click_at >= 4:
                    clicked_challenge, point = await _try_click_turnstile_challenge(page, attempt=challenge_attempts)
                    if clicked_challenge:
                        challenge_attempts += 1
                        last_challenge_click_at = now
                        log.info(f"检测到 Turnstile challenge frame, 已尝试点击验证区域: {point}.")
                        await asyncio.sleep(2)
                        continue

                verification_passed = bool(token) or bool(snapshot.get("hasSuccessText")) or bool(targets)
                if not verification_passed:
                    await asyncio.sleep(1)
                    continue

                if not targets:
                    await asyncio.sleep(1)
                    continue

                target_text = targets[0]
                log.info(f"已检测到 Turnstile 自动验证完成, 准备点击页面按钮: {target_text}.")

                response = None
                clicked = False
                try:
                    async with page.expect_response(
                        lambda resp: _is_candidate_managed_response(resp, origin),
                        timeout=10000,
                    ) as response_info:
                        clicked = await _click_turnstile_action(page, target_text)
                    response = await response_info.value if clicked else None
                except PlaywrightTimeoutError:
                    pass

                if not clicked:
                    await asyncio.sleep(1)
                    continue

                clicked_action = True
                log.info(f"已自动点击页面按钮: {target_text}.")
                if response:
                    return await _classify_managed_response(response)
                await asyncio.sleep(2)

            snapshot = await _describe_turnstile_page(page)
            body_text = snapshot.get("bodyText") or ""
            if clicked_action:
                detail = _format_turnstile_detail(body_text) or "已点击签到按钮, 但页面未返回明确结果"
                log.warning(f"已点击签到按钮, 但在等待时限内未观察到最终结果: {detail}.")
                return TurnstileManagedResult("fail", detail)

            detail = _format_turnstile_detail(body_text) or "页面未完成 Turnstile 自动验证"
            log.warning(f"本地 Turnstile 页面已打开, 但在等待时限内未通过验证: {detail}.")
            return TurnstileManagedResult("fail", detail)
    except PlaywrightTimeoutError:
        detail = "本地 Turnstile 页面加载超时，未能执行页面签到。"
        log.warning(detail)
        return TurnstileManagedResult("fail", detail)
    except Exception as e:
        detail = _normalize_launch_error(str(e))
        log.warning(f"本地 Turnstile 托管页面处理失败: {detail}.")
        show_exception(e, regular=False)
        return TurnstileManagedResult("fail", detail)
    finally:
        if browser:
            await browser.close()


async def solve_turnstile_token(url: str, timeout: float = 180.0, log=None) -> Optional[str]:
    log = log or logger
    available, reason = diagnose_solver()
    if not available:
        log.warning(f"当前无法进行本地 Turnstile 过盾: {reason}.")
        return None

    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright

    proxy = _build_playwright_proxy()
    useragent = _build_playwright_useragent()
    deadline = asyncio.get_running_loop().time() + timeout

    browser = None
    try:
        async with async_playwright() as pw:
            log.info(
                f"已启动本地 Turnstile 检测, 正在打开验证页面 ({'使用代理' if proxy else '直连'})."
            )
            browser = await pw.chromium.launch(**_build_playwright_launch_kwargs(proxy))
            context = await browser.new_context(**_build_playwright_context_kwargs(useragent))
            await _apply_stealth_context(context)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=min(int(timeout * 1000), 45000))
            log.debug("Turnstile 验证页已完成初始加载, 开始轮询 token.")

            diagnosed = False
            advanced = False
            challenge_attempts = 0
            last_challenge_click_at = 0.0
            while asyncio.get_running_loop().time() < deadline:
                now = asyncio.get_running_loop().time()
                token = await _extract_turnstile_token(page)
                if token:
                    log.info("已成功获取 Turnstile token.")
                    return token
                snapshot = await _describe_turnstile_page(page)
                widget_count = len(snapshot.get("widgets") or [])
                field_count = snapshot.get("fieldCount") or 0
                body_text = truncate_str(snapshot.get("bodyText") or "", 160)
                actions = snapshot.get("actionCandidates") or []
                turnstile_failed = _classify_turnstile_validation_text(snapshot.get("bodyText"))
                if not diagnosed:
                    diagnosed = True
                    log.debug(
                        f"Turnstile 页面状态: title={snapshot.get('title') or '-'}, readyState={snapshot.get('readyState')}, "
                        f"widgets={widget_count}, fields={field_count}, "
                        f"actions={_summarize_turnstile_actions(actions)}, body={body_text}"
                    )
                if turnstile_failed:
                    detail = turnstile_failed.detail or "Cloudflare Turnstile 验证失败"
                    log.warning(f"检测到 Turnstile 验证失败状态: {detail}.")
                    return None
                if not advanced and not widget_count:
                    clickable_actions = [a for a in actions if a.get("text") and not a.get("disabled")]
                    if clickable_actions:
                        clicked, label = await _advance_turnstile_page(page)
                        if clicked:
                            advanced = True
                            log.info(f"检测到验证前置页面, 已自动点击按钮: {label}.")
                            try:
                                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                            except PlaywrightTimeoutError:
                                pass
                            await asyncio.sleep(2)
                            snapshot = await _describe_turnstile_page(page)
                            body_text = truncate_str(snapshot.get("bodyText") or "", 160)
                            actions = snapshot.get("actionCandidates") or []
                            log.debug(
                                f"点击前置按钮后页面状态: url={snapshot.get('url')}, title={snapshot.get('title') or '-'}, "
                                f"readyState={snapshot.get('readyState')}, widgets={len(snapshot.get('widgets') or [])}, "
                                f"fields={snapshot.get('fieldCount') or 0}, "
                                f"actions={_summarize_turnstile_actions(actions)}, body={body_text}"
                            )
                    elif diagnosed:
                        log.debug(
                            f"前置页面仍在等待按钮就绪: actions={_summarize_turnstile_actions(actions)}, body={body_text}"
                        )
                challenge_present = any(_is_turnstile_challenge_frame_url(frame.url) for frame in page.frames)
                if challenge_present and now - last_challenge_click_at >= 4:
                    clicked_challenge, point = await _try_click_turnstile_challenge(page, attempt=challenge_attempts)
                    if clicked_challenge:
                        challenge_attempts += 1
                        last_challenge_click_at = now
                        log.info(f"检测到 Turnstile challenge frame, 已尝试点击验证区域: {point}.")
                        await asyncio.sleep(2)
                        continue
                await asyncio.sleep(1)
            snapshot = await _describe_turnstile_page(page)
            widget_count = len(snapshot.get("widgets") or [])
            body_text = truncate_str(snapshot.get("bodyText") or "", 160)
            log.warning(
                f"本地 Turnstile 页面已打开, 但在等待时限内未获得 token。"
                f" 当前页面 title={snapshot.get('title') or '-'}, widgets={widget_count}, body={body_text}"
            )
            lowered_body = (snapshot.get("bodyText") or "").lower()
            if "supported browser" in lowered_body or "recaptcha challenge" in lowered_body:
                log.warning("当前浏览器会话被站点判定为不受支持浏览器, 未能进入验证码挑战页面。")
    except PlaywrightTimeoutError:
        log.warning("本地 Turnstile 页面加载超时，未获得 token。")
    except Exception as e:
        log.warning(f"本地 Turnstile 解析失败: {_normalize_launch_error(str(e))}.")
        show_exception(e, regular=False)
    finally:
        if browser:
            await browser.close()
    return None
