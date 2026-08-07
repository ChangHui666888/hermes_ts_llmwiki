# 后端 — News Platform V8 (FastAPI)

> 最后更新: 2026-08-07
> 技术栈: Python 3.12 · FastAPI 0.133.1 · SQLAlchemy 2.0 · PostgreSQL 16
> 部署: Docker 容器 (`news-platform-v8-backend-1`, 338MB 镜像)
> 网络: **仅 Tailscale 内网 (100.107.117.23)，非公网服务**

## 架构总览

```
FastAPI 应用入口: apps/api/main.py (title: "News Platform V8", version 8.0.0)
  ├── 公开端点 (21): dashboard / events / sources / search / map / stories / entities / news / categories / ads / auth
  ├── Admin JWT (32): admin / admin_config / rss_sources / entities / entity_relations / event_curation
  ├── Internal Token (7): internal / fetch_stats / deploy
  └── 根端点 (1): /

V1 标准约束 (2026-07-29 起):
  - 所有端点使用 Depends(get_db) 依赖注入（无手动 session 管理）
  - Pydantic 模型验证请求/响应
  - HTTP 异常一致性 (404/401/403)
  - 无硬编码 mock 数据
  - 启动事件 seed_config(): 幂等建 event_article_override/event_article_exclusion/fact 表 + 空库种子配置
```

## 全部 API 端点 (60 = 21 公开 + 32 admin + 7 internal)

### 公开端点 (无需认证)

| 方法  | 路径                   | 模块              | 说明                                     |
| --- | -------------------- | --------------- | -------------------------------------- |
| GET | `/`                  | main.py         | 服务信息 `{"service": "News Platform V8"}` |
| GET | `/news`              | news.py         | 文章列表 (分页, 支持 category/tier/source 筛选, `sort=time_desc\|time_asc\|score_desc\|score_asc`, 默认 time_desc) |
| GET | `/news/hot`          | news.py         | Top 10 热门文章 (按 score_total 降序)         |
| GET | `/news/latest`       | news.py         | 最新 20 篇文章 (按 published_at 降序)          |
| GET | `/news/search`       | news.py         | 文章搜索 (title + summary_cn ilike)        |
| GET | `/news/{id}`         | news.py         | 文章详情 (无 token → 公开字段; VIP/Admin → 全文, summary 自动回退) |
| GET | `/categories`        | categories.py   | 文章分类计数                                 |
| GET | `/dashboard`         | dashboard_v1.py | 仪表盘 (KPI 含 `total_events` 全量; `stage_breakdown` 阶段分布; `event_type_breakdown` 类型分布 + Hot Events + 地图事件) |
| GET | `/events`            | events_v1.py    | 事件列表 (分页, 支持 type/location/stage 筛选, `sort=first_seen_desc\|first_seen_asc\|last_updated_*\|confidence_*`, 默认 first_seen_desc, NULL 排末尾; **读层去重**: 按 `lower(title)` 分组每组保留最佳行 article_count 大→last_updated 新→event_id 新, `total` 为去重后计数) |
| GET | `/events/{event_id}` | events_v1.py    | 事件 Dossier 详情                          |
| GET | `/events/{event_id}/relations` | events_v1.py | **事件-事件关系** (precedes/leads_to 等, 方向+时间范围) |
| GET | `/sources`           | sources_v1.py   | 来源注册表 (真实 event_count/article_count/权威度) |
| GET | `/search`            | search_v1.py    | 事件全文搜索 (title + summary ilike)         |
| GET | `/map/events`        | map_v1.py       | 地理事件标记 (`limit` 默认50/最大1000, 返回 `total` 带地点事件总数, 不再静默截断) |
| GET | `/api/v1/stories` | stories.py | **Story 列表** (含事件数, 按事件数降序; `?dimension=subject\|action\|object\|location` 过滤; 响应含 `derived_at`/`total_events`/`by_dimension` 分维统计) |
| GET | `/api/v1/stories/{id}` | stories.py | **Story 详情** (事件时间线, 按 position 排序) |
| POST | `/api/v1/stories/derive` | stories.py | **派生/重建故事** (admin; `?dimension=all\|subject\|action\|object\|location`, 默认 all 重建四维; 幂等 + 并发锁(409) + 审计日志; 返回 stories/derived_at/total_events/by_dimension) |
| GET | `/ads/random`        | ads.py          | 随机广告 (按 position 筛选)                   |
| GET | `/api/v1/entities` | entities.py | **实体列表** (按事件出现次数排序, 来自事件 subject/object/actors + KB) |
| GET | `/api/v1/entities/{name}` | entities.py | **实体画像** (国家归属+关联网络+相关事件+统计 event_count/article_count) |
| GET | `/admin/entities` | entities.py | **实体管理**: 当前 KB + 校验报告 |
| POST | `/admin/entities/save` | entities.py | **实体管理**: 保存整份 KB (校验→写 JSON+生成 py, 热生效; dry_run 仅校验) |
| POST | `/admin/entities/git-sync` | entities.py | **实体管理**: 容器内 git 提交推送实体文件 (safe.directory+身份) |
| GET | `/admin/entity-relations` | entity_relations.py | **实体关系管理 (v0.2)**: 全量实体+别名+实体关系+事件关系 |
| POST | `/admin/entity-relations` | entity_relations.py | **实体关系**: 新增 (from/to/type/desc) |
| DELETE | `/admin/entity-relations/{id}` | entity_relations.py | **实体关系**: 删除 |
| DELETE | `/admin/event-relations/{id}` | entity_relations.py | **事件关系**: 删除 |
| POST | `/admin/entity-relations/regenerate` | entity_relations.py | **重新生成**: 从 KB+事件派生重建关系 (跑 backfill) |

### 认证端点

| 方法 | 路径 | 模块 | 说明 |
|------|------|------|------|
| POST | `/auth/login` | auth.py | 登录 → JWT Token (HS256, 7天过期) |
| POST | `/auth/register` | auth.py | 注册新用户 (bcrypt 密码) |
| GET | `/auth/me` | auth.py | 当前用户信息 (需 Bearer Token) |

### 管理端点 (需 admin 权限)

| 方法 | 路径 | 模块 | 说明 |
|------|------|------|------|
| GET | `/admin/dashboard` | admin.py | 管理统计 (文章/用户/广告) |
| GET | `/admin/pipeline/status` | admin.py | **Pipeline 状态** (DB统计+事件分布+最近活动) |
| GET | `/admin/pipeline/config` | admin_config.py | 配置列表(9组~70项, 分组返回+元信息) |
| GET | `/admin/pipeline/config/seed` | admin_config.py | 种子配置(不含DB覆盖,对比差异) |
| GET | `/admin/pipeline/config/export` | admin_config.py | 完整配置导出 (admin) |
| GET | `/admin/pipeline/config/export-internal` | admin_config.py | 内部配置导出 (INTERNAL_TOKEN, 本地agent轮询用) |
| PUT | `/admin/pipeline/config/{key}` | admin_config.py | 更新单条配置 (保存后实时推送本地) |
| POST | `/admin/pipeline/config/batch` | admin_config.py | 批量更新配置 |
| POST | `/admin/pipeline/config/reset` | admin_config.py | 重置配置到默认值 |
| GET | `/admin/rss/sources` | rss_sources.py | RSS 源列表 (98源, 配置覆盖) |
| POST | `/admin/rss/sources` | rss_sources.py | **添加 RSS 源** |
| PUT | `/admin/rss/sources/{name}` | rss_sources.py | **编辑 RSS 源** |
| DELETE | `/admin/rss/sources/{name}` | rss_sources.py | **删除 RSS 源** |
| POST | `/admin/rss/sources/{name}/toggle` | rss_sources.py | **启用/禁用 RSS 源** |
| GET | `/admin/rss/profiles` | rss_sources.py | 域名抓取策略 (22域名) |
| GET | `/admin/curation/events` | event_curation.py | **手动聚合** 事件列表(含聚合/覆盖/剔除数) |
| GET | `/admin/curation/events/{id}` | event_curation.py | 事件"被聚合的文章"(自动+手动-排除, 含勾选态) |
| GET | `/admin/curation/articles` | event_curation.py | 文章列表/搜索 (`subject`实体/`object`实体/`action`动作词/`keyword`全文) |
| POST | `/admin/curation/batch` | event_curation.py | **批量提交** add/remove override + exclude/unexclude (单事务) |
| POST | `/admin/curation/events` | event_curation.py | 多选文章 → 自动生成元数据 → 新建事件并归入全部 |
| POST | `/admin/curation/assign` | event_curation.py | (兼容) 单篇归入 |
| DELETE | `/admin/curation/assign` | event_curation.py | (兼容) 移除手动归属 |

### 内部端点 (需 INTERNAL_TOKEN)

| 方法 | 路径 | 模块 | 说明 |
|------|------|------|------|
| POST | `/internal/news/batch` | internal.py | Pipeline 推送文章 (批量, ON CONFLICT url DO UPDATE) |
| POST | `/internal/events/batch` | internal.py | Pipeline 推送事件 (批量, ON CONFLICT 更新全部字段) |
| POST | `/internal/events/delete` | internal.py | 删除云端重复事件 (事件归一用, body: `["EVT-..."]`, 先清引用表再删主行) |
| POST | `/internal/facts/batch` | internal.py | **Fact Layer V1.0** 推送 fact + fact_entity (混合抽取器产出, ON CONFLICT + 实体替换) |
| POST | `/internal/fetch_stats` | fetch_stats.py | Pipeline 推送抓取策略统计 |
| GET | `/internal/admin/fetch_stats` | fetch_stats.py | 查看抓取策略统计汇总 (admin JWT) |
| POST | `/internal/deploy` | deploy.py | HTTP 触发部署 (git pull + docker rebuild) |

### 前端管理页路由 (nginx 精确匹配)

| 路径 | 说明 |
|:-----|:-----|
| `/admin` | Admin Dashboard |
| `/admin/sources` | 来源注册表 (可排序表格) |
| `/admin/status` | Pipeline 状态页 |
| `/admin/pipeline` | Pipeline 配置 |
| `/config` | 配置中心 (13 Tab: RSS参数/Pipeline/AI增强/评分/聚合/抓取/源列表/域名/状态/事件校对/实体管理/实体关系/数据模型) |
| `/entities` | 实体中心 |
| `/entities/[name]` | 实体画像页 |

## 认证机制

```python
# 双算法兼容密码验证
def verify_password(password: str, hashed: str) -> bool:
    if ":" in hashed and not hashed.startswith("$2"):  # 旧版 SHA256(salt+password)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    return bcrypt.verify(password, hashed)              # 新版 bcrypt

# JWT 签发 (HS256, 7天)
def create_token(user_id: int, level: str) -> str:
    return jwt.encode(
        {"user_id": user_id, "level": level, 
         "exp": datetime.utcnow() + timedelta(days=7)},
        SECRET_KEY, algorithm="HS256",
    )
```

## 数据模型 (27 个 ORM 模型, 2026-08-07)

后端 ORM 模型 (27 表):
- **核心域 (4)**: Source / Article / Event / **Story**
- **实体/关系 (4)**: Entity / **EntityAlias** / **EntityRelationship** / **EventRelation**
- **Fact 层 (2)**: Fact / FactEntity
- **校对 (2)**: EventArticleOverride / EventArticleExclusion
- **用户/配置 (5)**: User / Ad / Category / Tag / Setting
- **其他 (3)**: Asset / Insight / Log
- **关联表 (7)**: ArticleCategory / ArticleTag / ArticleEntity / EventArticle / EventEntity / **StoryEvent** / Subscription

(VPS 额外 `fetch_stats` + `alembic_version` 不在 ORM; 迁移 0001 fact / 0002 entity / 0003 story 全已应用。)

参见 [database.md](database.md) 完整数据库文档。

## 文章内容安全策略

- **匿名用户**: 只能获取 `_public_fields()` — 不含 `content_md`, `analysis`, `key_points`
- **VIP/Admin**: 通过 JWT 验证后获取完整内容
- **公开字段**: id, url, title, summary_cn, source_name, source_domain, published_at, category, tier, score_total, tags, entities

## Pipeline 数据接收

```python
# POST /internal/news/batch
# 验证头: X-Internal-Token (环境变量 INTERNAL_TOKEN)
# 批量插入 + UPSERT: ON CONFLICT (url) DO UPDATE

# POST /internal/events/batch
# 验证头: X-Internal-Token (环境变量 INTERNAL_TOKEN)
# 批量插入 + UPSERT: ON CONFLICT (event_id) DO UPDATE
# 事件使用 SQLAlchemy text() 原生 SQL 插入 (30 字段)
```

## 后端依赖

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy>=2.0
psycopg2-binary>=2.9
pydantic>=2.0
python-jose[cryptography]>=3.3    (JWT)
python-multipart>=0.0.12
passlib[bcrypt]>=1.7              (密码哈希)
python-dotenv>=1.0
httpx>=0.27
```

## API 响应格式

```json
// 列表响应
{ "total": 512, "page": 1, "limit": 20, "items": [...] }

// 事件 Dossier 响应 (GET /events/{event_id})
{
  "event_id": "EVT-20260709-011",
  "title": "...",
  "event_type": "Military",
  "stage": "active",
  "confidence": 0.91,
  "coherence": 69.5,
  "subject": { "name": "", "type": "Other" },
  "action": { "type": "ATTACKS", "detail": "..." },
  "object": { "name": "Iran", "type": "Country" },
  "location": { "country": "United States" },
  "source": { "primary_source": "SRC_DW_NEWS", "source_count": 6 },
  "actors": [...],
  "keywords": ["Military", "Energy"],
  "related_entities": [...],
  "evidence": [{"quote": "...", "source": "DW News"}],
  "source_chain": [{"role": "break", "source_name": "DW News"}],
  "timeline": [{"time": "...", "update": "...", "source": "..."}],
  "llm_analysis": null
}
```

## Nginx 路由映射

```
/api/v1/*               → backend:8000 (dashboard/events/events/{id}/relations/sources/search/map/stories/entities)
/internal/*             → backend:8000/internal/* (Pipeline 推送 + fetch_stats + deploy)
/auth/*                 → backend:8000/auth/*
/admin/*                → backend:8000/admin/* (含 /admin/curation/* /admin/entity-relations /admin/rss/*)
/news*                  → backend:8000/news*
/categories             → backend:8000/categories
/ads/random             → backend:8000/ads/random
/docs · /openapi.json   → backend:8000 (FastAPI 文档)
/admin (精确)           → frontend:3000 (Next.js 管理页)
/*                      → frontend:3000 (Next.js)
```
