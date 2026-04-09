# Debian Docker 一键部署

## 这是什么

这篇文档只教一条路。

- 用 Docker 跑 `embykeeper`
- 自动进入网页模式
- 在网页里写 `config.toml`
- 在网页里点“执行一次”或者“开启定时”
- 用接口拿西瓜链接

你不用自己配 systemd。

你不用自己跑二进制。

## 先安装 Docker

在 Debian 服务器里执行下面这组命令。

```bash
sudo apt update
sudo apt install -y ca-certificates curl
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
```

## 一键启动

直接执行这一条命令。

```bash
mkdir -p /opt/embykeeper-deploy && docker rm -f embykeeper >/dev/null 2>&1 || true && docker run -d \
  --name embykeeper \
  --restart unless-stopped \
  -p 1818:1818 \
  -e TZ=Asia/Shanghai \
  -e EK_WEBPASS='请改成你自己的网页登录密码' \
  -e EK_XIGUA_API_TOKEN='请改成你自己的接口密钥' \
  -v /opt/embykeeper-deploy:/app \
  embykeeper/embykeeper
```

执行完以后，数据会放在这里：

```text
/opt/embykeeper-deploy/
├── config.toml
├── logs/
├── runtime.json
└── xigua/
```

## 打开网页

浏览器打开：

```text
http://你的服务器IP:1818
```

登录密码就是刚才写进 `EK_WEBPASS` 的值。

## 保存配置

登录后，打开配置页面。

把你的 Telegram 账号和站点写进去。

如果你要拿西瓜链接，就把 `xigua` 留在签到站点里。

点“保存配置”后，网页会直接写这个文件：

```text
/opt/embykeeper-deploy/config.toml
```

## 执行一次

打开控制台页面。

点“执行一次”。

这一步会：

1. 读取 `config.toml`
2. 跑一轮签到
3. 如果启用了 `xigua`，就刷新一次最新链接
4. 把日志直接显示在网页里

## 开启定时

还是在控制台页面。

点“开启定时”。

以后容器会一直在后台跑。

如果容器重启了，它会按 `runtime.json` 继续恢复状态。

如果你要停掉后台任务，就点“停止任务”。

## 获取西瓜链接

你的 AI Agent 每天只要请求这个地址：

```bash
curl -fsS "http://你的服务器IP:1818/api/xigua/latest?token=你自己的接口密钥"
```

返回里只看两个字段：

- `ok`
- `url`

如果 `ok` 是 `true`，就把 `url` 交给 AI Agent 去签到。

## 看日志

看容器状态：

```bash
docker ps
docker logs -f embykeeper
```

看西瓜最新结果：

```bash
cat /opt/embykeeper-deploy/xigua/latest.json
```

## 升级

执行这组命令：

```bash
docker pull embykeeper/embykeeper
docker rm -f embykeeper

docker run -d \
  --name embykeeper \
  --restart unless-stopped \
  -p 1818:1818 \
  -e TZ=Asia/Shanghai \
  -e EK_WEBPASS='请改成你自己的网页登录密码' \
  -e EK_XIGUA_API_TOKEN='请改成你自己的接口密钥' \
  -v /opt/embykeeper-deploy:/app \
  embykeeper/embykeeper
```
