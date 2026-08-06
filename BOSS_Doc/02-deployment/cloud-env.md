# 云主机环境

> 最后更新: 2026-07-29
> 
> **⚠️ 重要: VPS 入站仅 Tailscale 内网，出站走公网。非公网 Web 服务。**

## 基本信息

| 项目 | 值 |
|------|-----|
| 主机名 | `ss-usc-k8s-worker-9` |
| 公网 IP | `173.208.218.154` / `77.93.152.103` |
| Tailscale IP | `100.107.117.23` |
| OS | Ubuntu 24.04.4 LTS (Noble Numbat) |
| Kernel | `6.8.0-136-generic` x86_64 |
| 内存 | 3.8 GB (空闲 2.9 GB) |
| 磁盘 | 63 GB (已用 40G / 67%) |
| Uptime | 1 day 14h |
| 时区 | UTC (系统级，未配置时区) |
| SSH 用户 | `administrator` |
| SSH 认证 | 密码: `root123root!@` |

### 网络接口

| 接口 | IP | 用途 |
|------|-----|------|
| `enp21s0` | 173.208.218.154/26 | 公网主 IP |
| `enp22s0` | 77.93.152.103/24 | 公网副 IP |
| `tailscale0` | 100.107.117.23/32 | Tailscale 内网 |
| `docker0` | 172.17.0.1/16 | Docker 网桥 |

### 域名解析

```
100.107.117.23 → ss-usc-k8s-worker-9 (Tailscale)
```

### 🌐 网络拓扑

```
┌─────────────────────────────────────────────────────┐
│  公网 (Public Internet)                              │
│  本地 → RSS/抓取 / git push                          │
│  VPS → GitHub / Docker Hub / LLM API                │
│  全部出站走公网                                      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Tailscale 内网 (100.x.x.x)                          │
│  本地 → VPS :80 (Web / Pipeline推送)                 │
│  本地 → VPS :22 (SSH 部署)                           │
│  仅本地↔VPS 双向入站                                  │
└─────────────────────────────────────────────────────┘
```

入站只有 Tailscale，出站全部走公网。

### 入站/出站矩阵

| 流量方向 | 路径 | 网络 | 说明 |
|:---------|:-----|:----|:------|
| 本地 → RSS 源 | 公网直连 | 🌐 公网 | RSS 扫描、全文抓取 |
| 本地 → GitHub | `git push` | 🌐 公网 | 代码提交 |
| 本地 → VPS | SSH/HTTP | 🔒 Tailscale | 部署、访问Web、Pipeline推送 |
| VPS → GitHub | `git pull` | 🌐 公网 | 拉取更新 |
| VPS → Docker Hub | `docker pull` | 🌐 公网 | 拉取镜像 |
| VPS → API | httpx | 🌐 公网 | DeepSeek/Qwen3 LLM 调用 |
| 外网 → VPS :80 | ❌ 拒绝 | — | 不提供公网 Web 服务 |

### 监听端口

| 端口 | 服务 | 访问限制 |
|:----:|------|:--------:|
| 22 | SSH | Tailscale 内网 + 密码认证 |
| 80 | Nginx (Web 统一入口) | **Tailscale 内网** (不绑定公网) |
| 443 | sing-box VLESS (VPN 代理) | 公网 (用于出站代理) |
| 8080 | SearXNG 搜索引擎 | Docker 内网 |
| 6010 | 内部服务 | Docker 内网 |

---

## Docker 环境

| 工具 | 版本 |
|------|------|
| Docker Engine | 29.5.3 |
| Docker Compose | v5.1.4 |

### 运行中容器 (news-platform-v8)

| 容器名 | 镜像 | 状态 | 端口 |
|--------|------|------|:----:|
| news-platform-v8-nginx-1 | nginx:alpine | ✅ Up 38h | 80→80 |
| news-platform-v8-backend-1 | news-platform-v8-backend | ✅ Up 38h | 8000 |
| news-platform-v8-frontend-1 | news-platform-v8-frontend | ✅ Up 38h | 3000 |
| news-platform-v8-postgres-1 | postgres:16-alpine | ✅ Up 38h (healthy) | 5432 |

### 运行中容器 (基础设施)

| 容器名 | 镜像 | 状态 | 端口 | 用途 |
|--------|------|------|:----:|------|
| searxng-core | searxng/searxng:latest | ✅ Up 38h | 8080 | 元搜索引擎 |
| searxng-valkey | valkey/valkey:9-alpine | ✅ Up 38h | - | Redis 兼容缓存 |
| sing-box | ghcr.io/sagernet/sing-box | ✅ Up 38h | 443 | VLESS VPN 代理 |

### 已停止容器

| 容器名 | 状态 | 说明 |
|--------|------|------|
| news-intel-web-frontend-1 | Exited 2 周前 | 旧版 Sentinel V1 (已冻结) |
| news-intel-web-postgres-1 | Exited 2 周前 | 旧版 PostgreSQL (已冻结) |

### Docker 镜像

| 镜像 | 大小 | 说明 |
|------|:----:|------|
| news-platform-v8-backend | 338MB | FastAPI 后端 |
| news-platform-v8-frontend | 1.02GB | Next.js 16 前端 |
| postgres:16-alpine | 420MB | 数据库 |
| nginx:alpine | 93.3MB | 反向代理 |
| searxng/searxng:latest | 377MB | 元搜索引擎 |
| ghcr.io/sagernet/sing-box | 116MB | VPN 代理 |
| valkey/valkey:9-alpine | 65.7MB | 缓存 |

---

## docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: news_intel
      POSTGRES_USER: news_admin
      POSTGRES_PASSWORD: news_pass
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U news_admin -d news_intel"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      DATABASE_URL: postgresql://news_admin:news_pass@postgres:5432/news_intel
      INTERNAL_TOKEN: ${INTERNAL_TOKEN:-v8-pipeline-token-2026-xK9mP2sR7wQ}
      JWT_SECRET: ${JWT_SECRET:-v8-jwt-secret-2026-nY4fT8bV3mL}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build: ./frontend
    environment:
      - NEXT_PUBLIC_API_URL=/api/v1
    restart: unless-stopped
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "80:80"
    restart: unless-stopped
    depends_on:
      - frontend

volumes:
  pgdata:
    external: true
    name: news-intel-platform_pgdata
```

---

## Nginx 配置

```nginx
server {
    listen 80;

    # Backend API routes
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /internal/ {
        proxy_pass http://backend:8000/internal/;
        proxy_set_header Host $host;
    }
    location /auth/ {
        proxy_pass http://backend:8000/auth/;
        proxy_set_header Host $host;
    }
    location /admin/ {
        proxy_pass http://backend:8000/admin/;
        proxy_set_header Host $host;
    }
    location /news {
        proxy_pass http://backend:8000/news;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /ads/ {
        proxy_pass http://backend:8000/ads/;
        proxy_set_header Host $host;
    }
    location /categories {
        proxy_pass http://backend:8000/categories;
        proxy_set_header Host $host;
    }
    location /docs {
        proxy_pass http://backend:8000/docs;
        proxy_set_header Host $host;
    }
    location /openapi.json {
        proxy_pass http://backend:8000/openapi.json;
        proxy_set_header Host $host;
    }

    # Frontend (所有其他请求)
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 数据库 (PostgreSQL)

| 项目 | 值 |
|------|-----|
| 数据库名 | `news_intel` |
| 用户 | `news_admin` |
| 密码 | `news_pass` |
| 连接串 | `postgresql://news_admin:news_pass@postgres:5432/news_intel` |
| 大小 | 15 MB |

### 数据量 (2026-08-06 VPS 实查)

| 表 | 行数 |
|----|:----:|
| events | ~200 (`/api/v1/dashboard` total_events=200; 重聚合后波动) |
| articles | 增长中 (08-03 为 1719) |
| entities | 60 |
| sources | 24 |

---

## 项目结构 (news-platform-v8)

```
/home/administrator/news-platform-v8/
├── apps/api/               # FastAPI 后端
│   ├── main.py             # 入口 (FastAPI, 40+ 路由: 公开/认证/管理/内部/V1)
│   ├── database.py         # SQLAlchemy + PostgreSQL
│   ├── models.py           # 18 表 ORM
│   ├── schemas.py          # Pydantic 模型
│   └── routes/             # 19 路由文件 (2026-08-06 补充)
│       ├── news.py         # 文章 CRUD
│       ├── internal.py     # Pipeline 数据接收
│       ├── auth.py         # JWT 认证
│       ├── admin.py        # 管理后台
│       ├── ads.py          # 广告
│       ├── categories.py   # 分类
│       ├── admin_config.py # 配置管理
│       ├── dashboard_v1.py # Sentinel 仪表盘
│       ├── events_v1.py    # 事件查询
│       ├── sources_v1.py   # 来源网络
│       ├── search_v1.py    # 搜索
│       ├── map_v1.py       # 地图
│       ├── entities.py     # 实体画像/别名/关系
│       ├── entity_relations.py # 实体关系管理 (配置中心)
│       ├── event_curation.py   # 事件校对
│       ├── stories.py      # Story 打包
│       ├── fetch_stats.py  # 抓取策略统计
│       ├── rss_sources.py  # RSS 源管理
│       └── deploy.py       # 部署
├── frontend/               # Next.js 16 前端
│   └── src/app/            # 12 页面
├── docs/                   # 文档
├── data/                   # 数据
├── docker-compose.yml
├── Dockerfile.backend
├── nginx.conf
└── README.md
```

---

## 部署操作

```bash
# SSH 连接
ssh administrator@100.107.117.23

# 查看容器状态
docker compose ps

# 查看日志
docker compose logs backend --tail=50
docker compose logs frontend --tail=50
docker compose logs nginx --tail=20

# 重启服务
docker compose restart nginx
docker compose restart backend

# 重建并启动
docker compose up -d --build

# 数据库查询
docker exec news-platform-v8-postgres-1 psql -U news_admin -d news_intel -c "SELECT count(*) FROM events"

# 检查 API
curl localhost:80/api/v1/dashboard
curl localhost:80/api/v1/events?limit=5
```

---

## 已知问题

1. **SQLite WAL 挂载问题**: Docker volume `:ro` 导致 SQLite 无法创建 WAL journal 文件 (已归档，当前使用 PostgreSQL)
2. **无 UFW 防火墙**: `ufw not enabled`，防火墙未启用
3. **磁盘使用 67%**: 63GB 已用 40G，2.49GB n8n 镜像占用较大
4. **sing-box 代理**: 占用 443 端口作为 VLESS VPN 入口
