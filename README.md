[![build status](https://img.shields.io/github/actions/workflow/status/emby-keeper/emby-keeper/ci.yml?branch=main)](https://github.com/emby-keeper/emby-keeper/commits/main) [![pypi badge](https://img.shields.io/pypi/v/embykeeper)](https://pypi.org/project/embykeeper/) [![docker](https://img.shields.io/docker/v/embykeeper/embykeeper?label=docker)](https://hub.docker.com/r/embykeeper/embykeeper) [![docker pulls](https://img.shields.io/docker/pulls/embykeeper/embykeeper?label=pulls)](https://hub.docker.com/r/embykeeper/embykeeper) [![license badge](https://img.shields.io/github/license/emby-keeper/emby-keeper)](https://github.com/emby-keeper/emby-keeper/blob/main/LICENSE) [![telegram badge](https://img.shields.io/badge/telegram-bot-blue)](https://t.me/embykeeper_bot) [![telegram badge](https://img.shields.io/badge/telegram-channel-green)](https://t.me/embykeeper) [![telegram badge](https://img.shields.io/badge/telegram-group-violet)](https://t.me/embykeeperchat)

<p align="center">
  <a href='https://github.com/emby-keeper/emby-keeper'>
    <img src="https://github.com/emby-keeper/emby-keeper/raw/main/images/logo.svg" alt="Embykeeper" />
  </a>
</p>
<p align="center">
    <b>自动签到 定时保号</b>
</p>

---

## 功能

Embykeeper 是一个专注于 Emby 影视服务器签到保号的自动执行工具, 核心功能只有两项:

1. **TG 机器人签到** - 可以自动完成 50+ 站点的 Telegram 机器人每日签到, 以获取积分.

2. **Emby 保号** - 通过模拟登录和播放视频, 定期保持 Emby 账号的活跃状态, 支持任何 Emby 站点.

项目支持 Python 运行与 Docker 部署, 且完全开源, 不存储任何密钥或隐私信息.

验证码识别、视觉题、文本推断和日志推送都可以通过本地 OpenAI 兼容模型与您自己的 Telegram Bot 完成, 不依赖作者机器人.

## 声明

本项目涉及的一切 Emby 服务器与 Embykeeper 开发团队无关, 在使用 Embykeeper 时造成的一切损失 (包括但不限于 Emby 或 Telegram 账号被封禁或被群封禁) 与开发团队无关. 为了您的账号安全, 推荐使用小号. 运行该工具的 Telegram 账号若通过接码注册, 请使用一段时间再接入本工具.

本项目设计初衷是在中文 Emby 社群规则下, 保号要求逐渐苛刻 (部分要求每月登录或每日签到), 这使得休闲时间紧张的人士难以安心使用. 本项目仅旨在帮助该类人群保号, 不鼓励持有大量 Emby 账号而不使用, 导致真正需要的人、为中文影视资源分享和翻译有贡献的人难以获得账号的行为, 开发团队也呼吁仅保留 1-2 个较全面质量较高的 Emby 服务器. 本项目仅提供工具, 具体使用形式及造成的影响和后果与开发团队无关.

验证码识别、智能回复和日志推送均改为本地 LLM 与您自己的 Telegram Bot 配置完成, 不再依赖作者机器人, 也不会把账号密钥发送给第三方服务.

当您安装并使用该工具, 默认您已经阅读并同意上述声明, 并确认自己并非出于"集邮"目的而安装.

## 安装与使用

Embykeeper 支持 Docker 或 PyPI 安装 (Linux / Windows), 请点击下方按钮查看安装指南:

[![Setup Tutorial](https://github.com/emby-keeper/emby-keeper/raw/main/images/setup-button.svg)](https://emby-keeper.github.io/guide/安装指南)

若您有服务器, 我们推荐使用 [Docker 部署](https://emby-keeper.github.io/guide/Linux-Docker-部署):

```bash
docker run -v $(pwd)/embykeeper:/app --rm -it --net=host embykeeper/embykeeper -i
```

**注意**: 由于近期 Telegram 风控等级上升, 请尽可能先使用服务器所在地区的代理在手机上先登陆一次, 再使用 Embykeeper.

您也可以使用 [Docker Compose 部署](https://emby-keeper.github.io/guide/Linux-Docker-Compose-部署).

更多安装和配置方面的帮助请参考 [**📖 教程文档**](https://emby-keeper.github.io/).

本项目欢迎友善讨论与建议, 您可以通过 [Github Issue](https://github.com/emby-keeper/emby-keeper) 途径反馈, 并认可开发团队可以关闭与项目开发不直接相关的不友善讨论. 您也可以通过 [Telegram 讨论群](https://t.me/embykeeper_chat_bot) 获得社区帮助.

## 运行截图

![Screenshot](https://github.com/emby-keeper/emby-keeper/raw/main/images/screenshot.png)

## 完整功能支持列表

- **Emby 保活**
  - 定时模拟账号登录视频播放
  - 播放时间与进度模拟
- **Telegram 机器人签到**
  <!-- #region checkiner-sites -->

  - 终点站 (`terminus`): [频道](https://t.me/embypub) [群组](https://t.me/EmbyPublic) [机器人](https://t.me/EmbyPublicBot)
  - Nebula (`nebula`): [频道](https://t.me/Nebula_Emby) [群组](https://t.me/NebulaEmbyUser) [机器人](https://t.me/Nebula_Account_bot)
  - 飞跃彩虹 (`feiyue`): [频道](https://t.me/fyemby) [群组](https://t.me/feiyueemby) [机器人](https://t.me/FeiyueEmby_bot)
  - PandaTV: [频道](https://t.me/PandaTV_Emby_Channel)
    - 自动签到 (`pandatv`): [机器人](https://t.me/PandaTV_Emby_Bot)
    - 每 14 天自动群里发送签到 (`pandatv_group`): [群组](https://t.me/PandaTV_Emby_Group)
  - Peach (`peach`): [机器人](https://t.me/peach_emby_bot)
  - 开心服 (`happy`): [频道](https://t.me/hhappyemby) [群组](https://t.me/Happyembyyds) [机器人](https://t.me/happy_sign_bot)
  - MICU (`micu`): [频道](http://t.me/+_PcX8rALVA80NTU1) [群组](http://t.me/+tW5vUYJROcE2ZTA1) [机器人](https://t.me/micu_user_bot)
  - 叔服Emby (`shufu`): [群组](http://t.me/+4eq37Ip8ayRhNDI9) [机器人](https://t.me/dashu660_bot)
  - 天南小筑 US (`tiannanus`): [频道](http://t.me/Nanflix) [群组](http://t.me/+kDBdjwtZwudhYWE1) [机器人](https://t.me/US_nan_bot)
  - Pilipili (`pilipili`): [频道](https://t.me/PiliPiliTv) [群组](http://t.me/PiliPiliTv) [机器人](https://t.me/PiliPiliUltraTv_bot)
  - CC 公益 (`cc`): [频道](https://t.me/CcEmby) [群组](https://t.me/Embycc) [机器人](https://t.me/EmbyCc_bot)
  - 卡戎 (`charon`): [频道](https://t.me/CharonTV) [群组](https://t.me/CharonTV_Talk) [机器人](https://t.me/CharonTV_Bot)
  - 未响 (`future`): [频道](https://t.me/FutureEcho_Notice) [群组](https://t.me/FutureEcho_Chat) [机器人](https://t.me/lotayu_bot)
  - AWA 影视服 (`awatv`): [频道](https://t.me/awa_tv) [群组](https://t.me/awatv_chat) [机器人](https://t.me/awatv3_bot)
  - 见手青 (`jsq`): [频道](https://t.me/jsq_channel) [群组](https://t.me/jsq_group) [机器人](https://t.me/jsq_gy_bot)
  - DVFilm (`dvfilm`): [频道](https://t.me/dvfilmupdating) [机器人](https://t.me/DVfilm_user_bot)
  - Lyrebird (`lyrebird`): [频道](https://t.me/lyrebirdchannel) [群组](https://t.me/lyrebirdchat) [机器人](https://t.me/Lyrebird_bot)
  - 非越助手 (`sfcju`): [频道](https://t.me/sfcj_org) [群组](https://t.me/sfcj_chat) [机器人](https://t.me/sfcju_Bot)
  - Yomo (`yomo`): [频道](https://t.me/yomoemby_notice) [群组](https://t.me/yomoemby) [机器人](https://t.me/yomoemby_bot)
  - AIVBI (`aivbi`): [频道](https://t.me/plus_emby) [群组](https://t.me/plusemby) [机器人](https://t.me/AIVBIbot)
  - Alpha 海外服 (`alpha`): [频道](https://t.me/AlphaTVOverseaChannel) [群组](https://t.me/AlphaTVOverseaGroup) [机器人](https://t.me/AlphaTVOverseaBoss_bot)
  - 月饼 (`mooncake`): [频道](https://t.me/Mooncake_notify) [群组](https://t.me/Mooncake_Emby) [机器人](https://t.me/Moonkkbot)
  - Plumber (`plumber`): [频道](http://t.me/PlumberEmby) [群组](http://t.me/+S060mYNUi1xlODlh) [机器人](https://t.me/Luuuigi_bot)
  - 飞跃地平线 (`feiyuedpx`): [频道](https://t.me/dpxpindao) [群组](https://t.me/+vHiy1TBnnjNiOWU1) [机器人](https://t.me/feiyueDPX_bot)
  - Levilde Luminia (`levilde`): [频道](https://t.me/+X5jJKAnbkl8wNWNl) [群组](https://t.me/+LzAmejEBy-I4N2E1) [机器人](https://t.me/Levilde_Luminia_Bot)
  - 收束世界线 (`worldline`): [机器人](https://t.me/WorldLineEmby_bot)
  - 飞跃星空 (`feiyuemusic`): [群组](https://t.me/+FVPdVkpM8moyNjc1) [机器人](https://t.me/xingkongmusic_bot)
  - Misty (`misty`): [频道](https://t.me/FreeEmbyChannel) [群组](https://t.me/FreeEmby) [机器人](https://t.me/EmbyMistyBot)
  - 探花 (`tanhua`): [频道](https://t.me/tanhua_tv2024) [群组](https://t.me/tanhuatv2025) [机器人](https://t.me/TanhuaTvBot)
  - iKun 音乐服 (`ikunmusic`): [频道](https://t.me/Asukacute) [群组](https://t.me/ikunvv) [机器人](https://t.me/iikun_bot)
  - HKA (`hka`): [群组](https://t.me/hkaemby) [机器人](https://t.me/hkaemby_bot)
  - SaturDay.Lite (`saturday`): [频道](https://t.me/saturday_lite_channel) [群组](https://t.me/SaturDay_Lite) [机器人](https://t.me/saturday_lite_bot)
  - 起点站: [群组](https://t.me/tdckemby)
    - 新机器人 (`tdck_new`): [机器人](https://t.me/StartTdckBot)
    - 旧机器人 (`tdck`) [机器人](https://t.me/tdck_emby_create_bot)
  - 惊蛰 (`jingzhe`): [频道](https://t.me/jz_emby) [群组](https://t.me/jingzhe_EMBY) [机器人](https://t.me/JingzheProbot)
  - 墨云阁 (`moyunge`): [频道](https://t.me/q98e1VZocwxkZDc1) [群组](https://t.me/mobaishishuaige) [机器人](https://t.me/MoYunGeBoss_bot)
  - 电子书库: [频道](https://t.me/bookhsulife) [群组](https://t.me/libhsulife)
    - Emby 机器人签到 (`epub`): [机器人](https://t.me/akilecloud_bot)
    - 群组内签到 (`epub_group`): [群组](https://t.me/libhsulife) [机器人](https://t.me/zhruonanbot)
    - 群组内发送八条随机诗句消息 (`epub_group_chat`): [群组](https://t.me/libhsulife)
  - Kiku (`kiku`): [频道](https://t.me/KikuEmbyNotice) [群组](https://t.me/KikuEmbyChat) [机器人](https://t.me/kikuemby_bot)
  - 叶子 (`yezi`): [频道](https://t.me/yezi_emby) [群组](https://t.me/yeziemby) [机器人](https://t.me/yeziemby_bot)
  - 叶子高码 (`yezigm`): [频道](https://t.me/yezi_emby) [群组](https://t.me/yeziemby) [机器人](https://t.me/yezigm_bot)
  - Ask (`ask`): [频道](https://t.me/ask_uni) [群组](https://t.me/Ask_Universal) [机器人](https://t.me/askUniversal_bot)
  - Youno (`youno`): [频道](http://t.me/+jRxdcDjxgpViNDll) [群组](https://t.me/YounosEmby) [机器人](https://t.me/YounoEmbyAgain_bot)
  - Lemby (`lemby`): [频道](https://t.me/Lemby_Channel) [群组](https://t.me/Lemby_Group) [机器人](https://t.me/LembyPremium_BOT)
  - 南瓜音乐 (`nangua`): [频道](https://t.me/nanguadd) [群组](https://t.me/nanguade) [机器人](https://t.me/nanguaemby_bot)
  - 西瓜 (`xigua`): [频道](https://t.me/ChilledWatermelon) [群组](https://t.me/ChilledMelonGroup) [机器人](https://t.me/XiguaEmbyBot)
  - 飞了个喵 (`meow`): [频道](https://t.me/+UhFqaQIVs8A2ZDRl) [群组](https://t.me/gymeowfly) [机器人](https://t.me/gymeowfly_bot)
  - 青梅映画 (`qingmei`): [频道](http://t.me/qingmeiyinghuaemby01) [群组](http://t.me/qingmeiyinghuaemby) [机器人](https://t.me/qingmeiemby_bot)
  - Star : [频道](https://t.me/star_emby) [群组](https://t.me/star_emby_chat)
    - 可爱的机器人签到 (`star1`): [机器人](https://t.me/star_emby_bot)
    - 不可爱的机器人签到 (`star2`): [机器人](https://t.me/star_emby2_bot)
  - 入机 (`ruji`): [频道](https://t.me/rjMediatz) [群组](https://t.me/rjMedai) [机器人](https://t.me/ljembyfukh_bot)
  - 入境 (`rujing`): [群组](https://t.me/rjfemby) [机器人](https://t.me/rujingModie_bot)
  - 比比助手 (`bibi`): [频道](http://t.me/bbembychannel) [群组](http://t.me/+1ahL4frEF_5lZmNl) [机器人](https://t.me/BBFreeFilm_bot)


  <!-- #endregion checkiner-sites -->

  - **更多签到站**可通过站点模板继续扩展.

  - 测试中新签到器 (默认禁用):
    <!-- #region checkiner-beta-sites -->

    - PornFans: [频道](https://t.me/PornFansChannel) [群组](https://t.me/PornFans_Chat) [机器人](https://t.me/Porn_Emby_Bot)
      - 签到群自动发言打卡 (`pornfans_group`): [签到群](https://t.me/PornFans_Chat)
      - 游戏群自动发言打卡 (`pornfans_game_group`): [游戏群](https://t.me/embytestflight)
    - Temby (`temby`): [频道](https://t.me/tembychannel) [群组](https://t.me/tembygroup) [机器人](https://t.me/HiEmbyBot)
    - Temby 测试服 (`temby_beta`): [群组](https://t.me/tembybeta) [机器人](https://t.me/Temby_Bot)
    - Ciji (`ciji`): [机器人](https://t.me/MM_nastool_bot)
    - StarCat (`starcat`): [频道](https://t.me/StarCatEmby) [群组](https://t.me/StarCatEmby) [机器人](https://t.me/StarCatBot)
    - 音海拾贝 (`navidrome`): [频道](https://t.me/navidrom_notify) [群组](https://t.me/navidrom_talk) [机器人](https://t.me/navidrome_bot)

    <!-- #endregion checkiner-beta-sites -->
  - 关服, 无响应, 或已停用签到功能 (默认禁用):
    <!-- #region checkiner-ignored-sites -->

    - July (`july`): ~~[群组](https://t.me/July_emby) [机器人](https://t.me/NASTOOL7_bot)~~
    - Lily (`lily`): ~~[频道](https://t.me/lily_yaya) [群组](https://t.me/lilydeyaa) [机器人](https://t.me/lilyembybot)~~
    - MJJ (`mjj`): ~~[频道](https://t.me/YH_Emby) [群组](https://t.me/mjj_emby_Chat) [机器人](https://t.me/mjjemby_uesr_bot)~~
    - DPeak (`dpeak`): ~~[群组](https://t.me/EMBY_DPeak) [机器人](https://t.me/emby_dpeak_bot)~~
    - 鹅服 (`zm`): ~~[机器人](https://t.me/ZXCHSJSHbot)~~
    - AuroraMedia (`aurora`): ~~[频道](https://t.me/AuroraMedia2) [机器人](https://t.me/AuroraMedia1_bot)~~
    - Raismusic (`raismusic`): ~~[频道](https://t.me/raisemby_channel) [群组1](https://t.me/raismusic_group) [群组2](https://t.me/Raisembyg) [机器人](https://t.me/raismusicbot)~~
    - 天南小筑 (`tiannan`): ~~[频道](http://t.me/Nanflix) [群组](http://t.me/+kDBdjwtZwudhYWE1) [机器人](https://t.me/Nanflix_bot)~~
    - 魔法Emby (`magic`): ~~[频道](https://t.me/Magic_EmbyChannel) [群组](https://t.me/Magicemby) [机器人](https://t.me/Magic_EmbyBot)~~
    - 卷毛鼠 (`jms`): ~~[频道](https://t.me/CurlyMouse) [群组](https://t.me/Curly_Mouse) [机器人](https://t.me/jmsembybot)~~
    - Akuai (`akuai`): ~~[频道](https://t.me/Akuaitzpibgdao) [群组](https://t.me/ikuaiemby) [机器人](https://t.me/joulilibot)~~
    - 垃圾影音 (`ljyy`): ~~[群组](https://t.me/+3sP2A-fgeXg0ZmY1) [机器人](https://t.me/zckllflbot)~~
    - EmbyHub (`embyhub`): ~~[频道](https://t.me/embyhub) [群组](https://t.me/emby_hub) [机器人](https://t.me/EdHubot)~~
    - BlueSea (`bluesea`): ~~[群组](https://t.me/blueseachat) [机器人](https://t.me/blueseamusic_bot)~~
    - 卷毛鼠 IPTV (`jms_iptv`): ~~[频道](https://t.me/CurlyMouseIPTV) [群组](https://t.me/Curly_MouseIPTV) [机器人](https://t.me/JMSIPTV_bot)~~
    - Singularity (`singularity`): ~~[频道](https://t.me/Singularity_Emby_Channel) [群组](https://t.me/Singularity_Emby_Group) [机器人](https://t.me/Singularity_Emby_Bot)~~
    - 剧狗 (`judog`): ~~[频道](https://t.me/Mulgoreemby) [机器人](https://t.me/mulgorebot)~~
    - Heisi (`heisi`): ~~[频道](https://t.me/HeisiEm) [群组](https://t.me/HeisiYi) [机器人](https://t.me/HeisiheiBot)~~
    - 阿甘正传 (`theend`): ~~[群组](https://t.me/+5vRfDeGmOKNiMzU1) [机器人](https://t.me/theendemby_bot)~~
    - Apop (`apop`): ~~[频道](https://t.me/ApopCloud_Channel) [群组](https://t.me/apopcloud) [机器人](https://t.me/apopcloudemby_bot)~~
    - Apop Pro (`apoppro`): ~~[频道](https://t.me/ApopCloud_Channel) [群组](https://t.me/apopcloud) [机器人](https://t.me/apopembypro_bot)~~
    - Akile: [群组](https://t.me/akileChat)
      - 群组内签到 (`akile_group`): ~~[群组](https://t.me/akileChat) [机器人](https://t.me/akilecloud_bot)~~
      - 机器人签到 (`akile`): ~~[机器人](https://t.me/akilecloud_bot)~~
    - 尘烬 (`skysink`): ~~[频道](https://t.me/skysink) [机器人](https://t.me/kyououbot)~~
    - AWA 音乐服 (`awamusic`): ~~[频道](https://t.me/vpsliebiao) [群组](https://t.me/vpsliebiaochat) [机器人](https://t.me/awamm_bot)~~

    <!-- #endregion checkiner-ignored-sites -->
## 支持 Embykeeper

##### 开发者团队

- ~~[jackzzs](https://github.com/jackzzs)~~
- [zetxtech](https://github.com/zetxtech)

##### 通过[爱发电](https://afdian.com/a/jackzzs)赞助

![Kitty](https://github.com/emby-keeper/emby-keeper/raw/main/images/kitty.gif)
