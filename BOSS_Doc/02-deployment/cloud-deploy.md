# 云主机部署

## 环境

| 项 | 值 |
|------|------|
| IP | 100.107.117.23 |
| 系统 | Ubuntu |
| 用户 | administrator |
| Docker | 29.5.3 |

## 首次部署

```bash
# 1. 拉取代码
git clone https://github.com/ChangHui666888/news-intel-platform.git
cd news-intel-platform

# 2. 启动
docker compose up -d

# 3. 验证
curl http://localhost:8001/health
curl http://localhost:80/
```

## 重建

```bash
cd news-intel-platform
git pull
docker compose build --no-cache
docker compose up -d
```

## 安全

```bash
# 运行加固脚本（仅首次）
sudo bash cloud-secure.sh
```

加固后端口状态：
- 5432: 仅 Docker 内网
- 8001: 仅白名单 IP (100.126.188.44, 100.120.73.47)
- 80: 公开

## 管理员

```
admin@newsintel.com / admin123
```
