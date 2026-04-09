from ._templ_a import TemplateACheckin


class XiguaCheckin(TemplateACheckin):
    name = "西瓜"
    bot_username = "XiguaEmbyBot"
    bot_use_captcha = False
    bot_checkin_cmd = "/start"
    unsupported_reason = "当前版本已暂停该站点签到（依赖 Cloudflare Turnstile）"
