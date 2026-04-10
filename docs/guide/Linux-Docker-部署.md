# Linux Docker 部署

## 这是什么

这条路适合自己管服务器的人。

你不需要公开镜像。

你只做这几步：

1. 克隆仓库
2. 本地构建镜像
3. 启动容器
4. 打开网页配置和运行

## 克隆仓库

```bash
mkdir -p /opt/embykeeper
cd /opt/embykeeper
git clone -b dev-terminal https://github.com/Waioot/emby-keeper.git
cd emby-keeper
```

## 构建镜像

```bash
docker build -t embykeeper-local .
```

## 启动容器

```bash
mkdir -p /opt/embykeeper-data
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

默认网页登录密码是 `embykeeper`。

如果你要改密码，就多加一项：

```bash
-e EK_WEBPASS='你自己的新密码'
```

## 打开网页

```text
http://你的服务器IP:1818
```

## 配置和运行

登录后：

1. 打开配置页面
2. 保存 `config.toml`
3. 打开控制台页面
4. 点“执行一次”
5. 要长期跑就点“开启定时”

## 获取西瓜链接

```bash
curl -fsS "http://你的服务器IP:1818/api/xigua/latest?token=你自己的接口密钥"
```

## 查看日志

```bash
docker logs -f embykeeper
```

## 升级

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
