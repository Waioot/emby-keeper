# Docker 一键部署

## 这是什么

这条路最简单。

你只做三件事：

1. 启动 Docker 容器
2. 打开网页保存配置
3. 在网页里执行一次或者开启定时

## 一键启动

先准备数据目录：

```bash
mkdir -p /opt/embykeeper-deploy
```

再启动容器：

```bash
docker rm -f embykeeper >/dev/null 2>&1 || true

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

## 打开网页

浏览器打开：

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
