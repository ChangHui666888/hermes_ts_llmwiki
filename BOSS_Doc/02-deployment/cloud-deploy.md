# 云主机部署新闻平台 (news-platform-v8)

> 最后更新: 2026-07-29
> 架构: Next.js 16 + FastAPI + PostgreSQL + Nginx
> 参考: [云主机环境](cloud-env.md) 查看实时状态

## 仓库

| 用途 | URL |
|------|-----|
| 主仓库 | `https://github.com/ChangHui666888/hermes-agent-backup` |
| Web 独立 | `https://github.com/ChangHui666888/sentinel-intelligence` |

## 架构

```
http://100.107.117.23
        │
    Nginx (:80)
    reverse proxy
        │
  ┌─────┼──────┐
  │     │      │
/api/*  /*    /internal/*
/auth/*  │    /admin/*
  │     │      │
  └──┬──┘      │
     │         │
  FastAPI (:8000) ← Pipeline HTTP POST
  23 endpoints  (INTERNAL_TOKEN)
     │
  PostgreSQL (:5432)
  news_intel DB (15MB)
  events(512) + articles(936)
  sources(24)
```

## 首次部署

```bash
# 1. SSH 到云主机
ssh administrator@100.107.117.23

# 2. 拉取代码
cd /home/administrator
git clone <repo-url> news-platform-v8
cd news-platform-v8

# 3. 配置环境变量
export INTERNAL_TOKEN=v8-pipeline-token-2026-xK9mP2sR7wQ
export JWT_SECRET=v8-jwt-secret-2026-nY4fT8bV3mL

# 4. 启动所有服务
docker compose up -d --build

# 5. 验证
curl localhost:80/                    # Next.js 前端
curl localhost:80/api/v1/dashboard    # API 仪表盘
curl localhost:80/api/v1/events?limit=5  # 事件列表
curl localhost:80/docs                # API 文档 (Swagger)
```

## 日常更新

```bash
# 本地推送
git add -A && git commit -m "update" && git push

# 云端拉取重建
ssh administrator@100.107.117.23
cd /home/administrator/news-platform-v8
git pull
docker compose up -d --build
```

## 服务管理

```bash
# 查看状态
docker compose ps

# 单独查看日志
docker compose logs backend --tail=50
docker compose logs frontend --tail=50
docker compose logs nginx --tail=20

# 重启单个服务
docker compose restart nginx
docker compose restart backend

# 完全重建
docker compose down
docker compose up -d --build
```

## 数据同步 (本地 Pipeline → 云端)

```bash
# 本地执行 (Windows)
cd ~/AppData/Local/hermes/profiles/outside-deepdeek/skills/research/search-engine-v2/scripts
python auto-pipeline.py

# 或使用 cron-sync 简化版
python cron-sync.py
```

同步流程：
```
本地 news_intel.db → HTTP POST /internal/events/batch → PostgreSQL events 表
                   → HTTP POST /internal/news/batch  → PostgreSQL articles 表
```

## 验证

```bash
# API
curl http://100.107.117.23/api/v1/dashboard
# → {"metrics":{"active_events":512,"sources":24,...}}

# 数据库
docker exec news-platform-v8-postgres-1 psql -U news_admin -d news_intel \
  -c "SELECT count(*) FROM events; SELECT count(*) FROM articles;"
```

## 账号

```
管理员登录: admin@test.com / admin123
API Token:  v8-pipeline-token-2026-xK9mP2sR7wQ (INTERNAL_TOKEN)
JWT Secret: v8-jwt-secret-2026-nY4fT8bV3mL
```

## 已知问题

1. **无防火墙**: UFW 未启用，SSH 端口 22 和其他服务依赖 Docker 网络隔离
2. **磁盘 67%**: 63GB 磁盘已用 40G，注意 n8n 镜像占用 2.49GB
3. **旧版容器**: `news-intel-web-frontend-1` 和 `news-intel-web-postgres-1` 已停止 2+ 周，可清理释放资源
