# Debian Web 部署

## 这是什么

这个版本只走一条路。

- 你在 Debian 服务器上运行 `embykeeper-web`
- 你用浏览器打开网页
- 你在网页里保存 `config.toml`
- 你在网页里点“执行一次”或者“开启定时”
- 如果你开了 `xigua`，系统会把最新链接写到接口里

安装后的目录固定是这样：

```text
embykeeper-deploy/
├── embykeeper
├── embykeeper-web
├── config.toml
├── logs/
├── runtime.json
└── xigua/
```

## 安装

先准备一个空目录。

```bash
mkdir -p /opt/embykeeper
cd /opt/embykeeper
```

再运行安装命令。

```bash
curl -fsSL https://raw.githubusercontent.com/emby-keeper/emby-keeper/main/scripts/install-binary.sh | bash
```

装完以后，目录会是这样：

```text
/opt/embykeeper/embykeeper-deploy/
├── embykeeper
├── embykeeper-web
├── config.toml
├── logs/
├── runtime.json
└── xigua/
```

## 启动 Web 服务

把下面这段内容写进 systemd。

```bash
sudo tee /etc/systemd/system/embykeeper-web.service >/dev/null <<'SERVICE'
[Unit]
Description=Embykeeper Web
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/embykeeper/embykeeper-deploy
Environment=EK_BASEDIR=/opt/embykeeper/embykeeper-deploy
Environment=EK_WEBPASS=请改成你自己的网页登录密码
Environment=EK_XIGUA_API_TOKEN=请改成你自己的接口密钥
ExecStart=/opt/embykeeper/embykeeper-deploy/embykeeper-web --wait --port 1818
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE
```

启动服务。

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now embykeeper-web
sudo systemctl status embykeeper-web --no-pager
```

## 打开网页

浏览器打开：

```text
http://你的服务器IP:1818
```

登录密码就是你刚才写进 `EK_WEBPASS` 的值。

## 保存配置

登录后，先打开配置页面。

把你的账号和站点写进 `config.toml`。

最少要保证两件事：

1. 你的 `telegram.account` 是你自己的账号
2. `site.checkiner` 里写了你要签到的站点

如果你要产出西瓜链接，就把 `xigua` 留在里面。

保存后，网页会直接把内容写进这个文件：

```text
/opt/embykeeper/embykeeper-deploy/config.toml
```

## 执行一次

打开控制台页面。

点一下“执行一次”。

这一步会做这些事：

1. 读取 `config.toml`
2. 跑一轮签到
3. 如果开了 `xigua`，最后会刷新一次最新链接
4. 日志会直接显示在网页里

## 开启定时

还是在控制台页面。

点一下“开启定时”。

开启后，Web 会在后台长期运行。

它会按你的配置定时执行。

如果服务器重启了，Web 重新起来以后，会继续按 `runtime.json` 里的状态恢复。

如果你要停掉后台任务，就点“停止任务”。

## 获取西瓜链接

接口地址固定是：

```text
GET /api/xigua/latest
```

在本机或者别的机器上这样取：

```bash
curl -fsS "http://你的服务器IP:1818/api/xigua/latest?token=你自己的接口密钥"
```

正常会返回一段 JSON。

你只看这两个字段：

- `ok`
- `url`

如果 `ok` 是 `true`，就把 `url` 交给你的 AI Agent。

## 看日志

先看 Web 服务本身的状态。

```bash
sudo systemctl status embykeeper-web --no-pager
```

再看服务日志。

```bash
sudo journalctl -u embykeeper-web -n 200 --no-pager
```

如果你想看签到运行结果，再看部署目录里的日志文件。

```bash
tail -n 200 /opt/embykeeper/embykeeper-deploy/logs/*.log
```

如果你想直接看西瓜最新结果，就看这个文件。

```bash
cat /opt/embykeeper/embykeeper-deploy/xigua/latest.json
```

## 升级

先停掉 Web 服务。

```bash
sudo systemctl stop embykeeper-web
```

再回到安装目录，重新跑安装命令。

```bash
cd /opt/embykeeper
curl -fsSL https://raw.githubusercontent.com/emby-keeper/emby-keeper/main/scripts/install-binary.sh | bash
```

最后再启动服务。

```bash
sudo systemctl start embykeeper-web
```
