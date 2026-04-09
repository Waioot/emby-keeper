# Debian 本地构建 Docker 部署

## 这是什么

这篇文档只教一条路。

- 在服务器上克隆仓库
- 在服务器上本地构建镜像
- 用这个本地镜像启动 Web
- 在网页里保存 `config.toml`
- 在网页里点“执行一次”或者“开启定时”

镜像不会推到公开环境。

## 先安装 Docker 和 Git

在 Debian 服务器里执行：

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
```

## 克隆仓库

执行下面这组命令：

```bash
mkdir -p /opt/embykeeper
cd /opt/embykeeper
git clone https://github.com/emby-keeper/emby-keeper.git
cd emby-keeper
```

## 本地构建镜像

执行：

```bash
docker build -t embykeeper-local .
```

这一步会在你的服务器上生成一个本地镜像：

```text
embykeeper-local
```

## 启动容器

先准备数据目录：

```bash
mkdir -p /opt/embykeeper-data
```

再启动容器：

```bash
docker rm -f embykeeper >/dev/null 2>&1 || true

docker run -d \
  --name embykeeper \
  --restart unless-stopped \
  -p 1818:1818 \
  -e TZ=Asia/Shanghai \
  -e EK_XIGUA_API_TOKEN='请改成你自己的接口密钥' \
  -v /opt/embykeeper-data:/app \
  embykeeper-local
```

默认网页登录密码是：

```text
embykeeper
```

如果你要改密码，就用这条：

```bash
docker rm -f embykeeper >/dev/null 2>&1 || true

docker run -d \
  --name embykeeper \
  --restart unless-stopped \
  -p 1818:1818 \
  -e TZ=Asia/Shanghai \
  -e EK_WEBPASS='你自己的新密码' \
  -e EK_XIGUA_API_TOKEN='请改成你自己的接口密钥' \
  -v /opt/embykeeper-data:/app \
  embykeeper-local
```

数据会放在这里：

```text
/opt/embykeeper-data/
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

如果你没有改密码，登录密码就是：

```text
embykeeper
```

## 保存配置

登录后，打开配置页面。

把你的 Telegram 账号和站点写进去。

如果你要拿西瓜链接，就把 `xigua` 留在签到站点里。

点“保存配置”后，网页会直接写这个文件：

```text
/opt/embykeeper-data/config.toml
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

你的 AI Agent 每天请求这个地址：

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
cat /opt/embykeeper-data/xigua/latest.json
```

## 升级

先更新仓库，再重新构建，再重启容器。

```bash
cd /opt/embykeeper/emby-keeper
git pull
docker build -t embykeeper-local .
docker rm -f embykeeper

docker run -d \
  --name embykeeper \
  --restart unless-stopped \
  -p 1818:1818 \
  -e TZ=Asia/Shanghai \
  -e EK_XIGUA_API_TOKEN='请改成你自己的接口密钥' \
  -v /opt/embykeeper-data:/app \
  embykeeper-local
```
