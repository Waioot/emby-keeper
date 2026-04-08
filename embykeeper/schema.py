from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, model_validator, ValidationError
from pydantic.networks import HttpUrl

DEFAULT_TIME_RANGE = "<11:00AM,11:00PM>"
DEFAULT_EMBY_INTERVAL_DAYS = "<7,12>"


class ConfigModel(BaseModel):
    model_config = {"extra": "forbid"}

    @model_validator(mode="before")
    @classmethod
    def validate_extra_fields(cls, values):
        if not isinstance(values, dict):
            return values
        if cls.model_config.get("extra") == "allow":
            return values
        allowed_fields = set(cls.model_fields.keys())
        extra_fields = set(values.keys()) - allowed_fields
        if extra_fields:
            raise ValueError(
                f"包含未知设置项：{', '.join(extra_fields)}, 允许的设置项: {', '.join(allowed_fields)}"
            )
        return values


class UseStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        if isinstance(v, (int, float)):
            return str(v)
        return v


class UseHttpUrl(HttpUrl):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        if isinstance(v, str) and not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        return HttpUrl(v)

    def __str__(self):
        return str(self._url)


class ProxyConfig(ConfigModel):
    hostname: Optional[str] = None
    port: Optional[int] = Field(None, gt=0)
    scheme: Optional[str] = Field(None, pattern="^(socks5|http)$")
    username: Optional[str] = None
    password: Optional[str] = None


class LLMProfileConfig(ConfigModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    prompt: Optional[str] = None
    timeout: Optional[float] = 60.0
    retries: Optional[int] = 3
    temperature: Optional[float] = None
    image_detail: Optional[str] = "high"


class LLMConfig(ConfigModel):
    default: Optional[LLMProfileConfig] = LLMProfileConfig()
    ocr: Optional[LLMProfileConfig] = LLMProfileConfig()
    vision: Optional[LLMProfileConfig] = LLMProfileConfig()
    reasoning: Optional[LLMProfileConfig] = LLMProfileConfig()

    model_config = {"extra": "allow"}


class CheckinerConfig(ConfigModel):
    time_range: Optional[UseStr] = DEFAULT_TIME_RANGE
    interval_days: Optional[UseStr] = "1"
    timeout: Optional[int] = 120
    retries: Optional[int] = 4
    concurrency: Optional[int] = 1
    random_start: Optional[int] = 60

    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def reject_removed_fields(cls, values):
        if not isinstance(values, dict):
            return values
        removed = [
            "ai_base_url",
            "ai_model",
            "ai_api_key",
            "ocr_ai_base_url",
            "ocr_ai_model",
            "ocr_ai_api_key",
            "ocr_ai_prompt",
        ]
        used = [key for key in removed if key in values]
        if used:
            raise ValueError(f"以下配置项已移除，请改用 llm.*：{', '.join(used)}")
        return values

    def get_site_config(self, site: str) -> Dict[str, Any]:
        return getattr(self, site, {})


class MonitorConfig(ConfigModel):
    model_config = {"extra": "allow"}

    def get_site_config(self, site: str) -> Dict[str, Any]:
        return getattr(self, site, {})


class MessagerConfig(ConfigModel):
    model_config = {"extra": "allow"}

    def get_site_config(self, site: str) -> Dict[str, Any]:
        return getattr(self, site, {})


class RegistrarConfig(ConfigModel):
    concurrency: Optional[int] = 1

    model_config = {"extra": "allow"}

    def get_site_config(self, site: str) -> Dict[str, Any]:
        return getattr(self, site, {})


class NotifierTelegramBotConfig(ConfigModel):
    bot_token: Optional[str] = None
    chat_id: Optional[Union[int, str]] = None


class NotifierConfig(ConfigModel):
    enabled: Optional[bool] = False
    immediately: Optional[bool] = False
    once: Optional[bool] = False
    method: Optional[str] = "telegram_bot"
    apprise_uri: Optional[str] = None
    telegram_bot: Optional[NotifierTelegramBotConfig] = None

    @model_validator(mode="before")
    @classmethod
    def reject_removed_fields(cls, values):
        if not isinstance(values, dict):
            return values
        if values.get("method") == "telegram":
            raise ValueError('`notifier.method = "telegram"` 已移除，请改用 `"telegram_bot"`')
        if "account" in values:
            raise ValueError("`notifier.account` 已移除，请改用 notifier.telegram_bot.chat_id")
        return values


class SiteConfig(ConfigModel):
    checkiner: Optional[List[str]] = None
    monitor: Optional[List[str]] = None
    messager: Optional[List[str]] = None
    registrar: Optional[List[str]] = None


class MediaServerBaseConfig(ConfigModel):
    time_range: Optional[UseStr] = DEFAULT_TIME_RANGE
    interval_days: Optional[UseStr] = DEFAULT_EMBY_INTERVAL_DAYS
    concurrency: Optional[int] = 1
    retries: Optional[int] = 5


class EmbyAccount(ConfigModel):
    url: UseHttpUrl
    username: str
    password: str
    name: str = None
    time: Optional[Union[int, List[int]]] = [300, 600]
    useragent: Optional[str] = None
    client: Optional[str] = None
    client_version: Optional[str] = None
    device: Optional[str] = None
    device_id: Optional[str] = None
    allow_multiple: Optional[bool] = True
    allow_stream: Optional[bool] = False
    use_proxy: Optional[bool] = True
    play_id: Optional[str] = None
    enabled: Optional[bool] = True

    # 站点单独配置
    interval_days: Optional[Union[int, str]] = None
    time_range: Optional[str] = None


class EmbyConfig(MediaServerBaseConfig):
    account: Optional[List[EmbyAccount]] = []


class SubsonicAccount(ConfigModel):
    url: UseHttpUrl
    username: str
    password: str
    name: str = None
    time: Optional[Union[int, List[int]]] = None
    useragent: Optional[str] = None
    client: Optional[str] = None
    client_version: Optional[str] = None
    use_proxy: Optional[bool] = True
    enabled: Optional[bool] = True

    # 站点单独配置
    interval_days: Optional[Union[int, str]] = None
    time_range: Optional[str] = None


class SubsonicConfig(MediaServerBaseConfig):
    account: Optional[List[SubsonicAccount]] = []


class TelegramAccount(ConfigModel):
    phone: str = Field(description="Telegram phone number")

    @model_validator(mode="before")
    @classmethod
    def clean_phone(cls, values):
        if isinstance(values, dict) and "phone" in values:
            values["phone"] = values["phone"].replace(" ", "")
        return values

    checkiner: Optional[bool] = True
    monitor: Optional[bool] = False
    messager: Optional[bool] = False
    registrar: Optional[bool] = False
    api_id: Optional[str] = None
    api_hash: Optional[str] = None
    session: Optional[str] = None
    enabled: Optional[bool] = True

    # 账号单独配置
    site: Optional[SiteConfig] = None
    checkiner_config: Optional[CheckinerConfig] = None
    registrar_config: Optional[RegistrarConfig] = None

    def get_config_key(self):
        import hashlib

        unique_str = f"{self.phone}:{self.api_id or ''}:{self.api_hash or ''}"
        hash_value = hashlib.sha256(unique_str.encode()).hexdigest()[:8]
        return f"{self.phone}/{hash_value}"

    @staticmethod
    def get_phone_masked(phone: Optional[str]):
        if phone is None:
            return "unknown"
        phone = str(phone)
        phone_len = len(phone)
        if phone_len == 0:
            return "unknown"
        visible_part = max(1, phone_len // 3)
        return phone[:visible_part] + "*" * (phone_len - visible_part * 2) + phone[-visible_part:]


class TelegramConfig(ConfigModel):
    account: Optional[List[TelegramAccount]] = []
    use_proxy: Optional[bool] = True


class BotConfig(ConfigModel):
    token: str
    chat_id: Optional[Union[int, str]] = None


class Config(ConfigModel):
    mongodb: Optional[str] = None
    basedir: Optional[str] = None
    nofail: Optional[bool] = True
    noexit: Optional[bool] = False
    debug_cron: Optional[bool] = False
    proxy: Optional[ProxyConfig] = None
    llm: Optional[LLMConfig] = LLMConfig()
    emby: Optional[EmbyConfig] = EmbyConfig()
    subsonic: Optional[SubsonicConfig] = SubsonicConfig()
    checkiner: Optional[CheckinerConfig] = CheckinerConfig()
    monitor: Optional[MonitorConfig] = MonitorConfig()
    messager: Optional[MessagerConfig] = MessagerConfig()
    registrar: Optional[RegistrarConfig] = RegistrarConfig()
    telegram: Optional[TelegramConfig] = TelegramConfig()
    notifier: Optional[NotifierConfig] = NotifierConfig()
    site: Optional[SiteConfig] = None

    # 调试字段
    bot: Optional[BotConfig] = None


def format_errors(e: ValidationError) -> str:
    """自定义错误信息格式化"""

    error_translations = {
        "Input should be a valid boolean": "输入应为布尔值 (true/false)",
        "Input should be a valid integer": "输入应为有效的整数",
        "Input should be a valid string": "输入应为有效的字符串, 用英文双引号包裹",
        "Input should be a valid list": "输入应为有效的列表, 用[]符号包裹",
        "Input should be a valid URL": "输入应为有效的URL地址",
        "Field required": "必填字段",
        "Value error": "配置验证错误",
        "Input should match pattern": "输入格式不匹配要求",
        "Value is not a valid dict": "输入应为有效的字典格式",
    }

    error_groups = {}
    error_messages = ["配置文件错误, 请检查配置文件:"]

    for error in e.errors():
        location = list(error["loc"])
        msg = error["msg"]

        # 翻译错误消息
        for eng, chn in error_translations.items():
            if callable(chn):
                msg = msg.replace(eng, chn(error["loc"]))
            else:
                msg = msg.replace(eng, chn)

        if not location:
            error_messages.append(f"  {msg}")
            continue

        loc_str = " -> ".join(str(loc) for loc in location)

        error_key = (() if len(location) <= 1 else tuple(location[1:])) + (msg,)
        error_groups[error_key] = (f"  {loc_str}", msg)

    # 添加分组后的错误消息
    for _, (location, msg) in error_groups.items():
        error_messages.append(f"{location}:")
        error_messages.append(f"    {msg}")

    error_messages.append("详细说明请访问: https://emby-keeper.github.io/guide/配置文件")
    return "\n".join(error_messages)


if __name__ == "__main__":
    import sys
    import tomli

    if len(sys.argv) < 2:
        print("Usage: python schema.py <config.toml>")
        sys.exit(1)

    try:
        with open(sys.argv[1], "rb") as f:
            config_dict = tomli.load(f)
        config = Config(**config_dict)
        print(config.model_dump_json(indent=2))
    except FileNotFoundError:
        print(f"错误: 配置文件 '{sys.argv[1]}' 未找到")
        sys.exit(1)
    except tomli.TOMLDecodeError as e:
        print(f"错误: TOML格式无效 - {e}")
        sys.exit(1)
    except ValidationError as e:
        print(format_errors(e))
        sys.exit(1)
