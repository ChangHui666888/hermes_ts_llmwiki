# 前端 — Sentinel Intelligence (Next.js 16)

> 最后更新: 2026-08-07
> 技术栈: Next.js 16.2.10 · React 19.2.4 · TypeScript 5.9 · Tailwind CSS v4 · shadcn/ui
> 实际路径: `search-engine-v2/scripts/news-platform-v8/frontend/`（⚠️ 仓库根 `frontend/` 是陈旧副本，未被 git 跟踪、仅有 1 页，勿改）
> 部署: Docker 容器 (`news-platform-v8-frontend-1`, `node:20-alpine`)
> 网络: **仅 Tailscale 内网 (100.107.117.23)，非公网服务**

## 架构概览

```
scripts/news-platform-v8/frontend/src/
├── app/                   # Next.js App Router 页面 (21 页)
│   ├── layout.tsx         # 全局布局 (AuthProvider → Header + Sidebar + main)
│   ├── globals.css        # Tailwind v4 全局样式
│   ├── page.tsx           # 首页: 态势感知中心 (6 指标 + 类型分布 + 地图 + Hot + 热度 + 情报流)
│   ├── articles/          # 文章模块 (纽约时报风格)
│   │   ├── page.tsx / [id] / category/[name] / source/[name] / list
│   ├── events/            # 事件模块
│   │   ├── page.tsx       # 事件列表 (筛选/分页/排序)
│   │   └── [id]/page.tsx  # 事件 Dossier 详情 (7 子组件)
│   ├── stories/           # Story 演化层 (Phase 3c)
│   │   ├── page.tsx       # 故事列表 (按事件数降序)
│   │   └── [id]/page.tsx  # 故事时间线 v2 (垂直射线 + 点击就地展开事件)
│   ├── entities/          # 实体中心
│   │   ├── page.tsx       # 实体列表 (按事件次数排序 + 搜索)
│   │   └── [name]/page.tsx  # 实体画像 (国家归属 + 关联网络 + 相关事件 + 别名)
│   ├── search/page.tsx    # 全局搜索 (debounce 300ms)
│   ├── sources/page.tsx   # 来源注册表 (权威度柱状图)
│   ├── map/page.tsx       # 地理监控 V2 (MapLibre GL, 5区域/6类型筛选, hover 联动)
│   ├── login/page.tsx     # 登录页 (JWT)
│   ├── admin/             # 管理后台 (4 页)
│   │   ├── page.tsx / pipeline / sources / status
│   └── config/page.tsx    # 配置中心 (14 Tab, ~9 内联组件, 含"故事管理"重建按钮+结果对比面板)
├── lib/
│   ├── api.ts             # fetchAPI<T> 封装 (/api/v1)
│   ├── auth.tsx           # Auth Context (localStorage JWT + /auth/me 校验)
│   ├── country-coords.ts  # 195 国坐标库
│   ├── types.ts           # 类型重导出
│   └── utils.ts           # cn() class 合并
├── components/            # 19 组件
│   ├── layout/            # Header (Logo+搜索+UTC时钟+状态) / Sidebar (7 组菜单+阶段统计)
│   ├── dashboard/         # MetricCard / WorldMap(SVG) / MapLibreWorldMap(WebGL) / EventHeat / IntelligenceFeed
│   ├── event/             # EventCard / EventHeader / FactPanel / EvidenceCard / Timeline / SourceChain / RelationGraph(D3) / IntelligencePanel
│   ├── common/            # Badge (stage/confidence 变体)
│   └── ui/                # button (shadcn)
└── contracts/             # 冻结 API Contract (v1.0 + v8.0)
    ├── event.ts / dashboard.ts / source.ts / article.ts
```

**双地图实现**: 首页 `/` 用 `react-simple-maps` (SVG) + `/map` 用 `maplibre-gl` (WebGL, Carto dark-matter)。

## 页面路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | Dashboard | 态势感知中心：6 指标(含 Total Events 全量)、By Type 类型分布(点击过滤 /events)、世界地图、Hot Events、热度图、情报流；事件卡片含 国家/实体/时间线/更新时间 |
| `/articles` | 文章列表 | Hot(6篇) + Latest(12篇) + **顶部 6 组下拉主菜单**(/news/menu, 2026-08-08 替代源名tab) + 侧栏层级 + 来源分组(已归一化去重) |
| `/articles/[id]` | 文章详情 | VIP/Admin 可见全文 content_md |
| `/articles/category/[name]` | 分类筛选 | 按主题分类查看文章 |
| `/articles/source/[name]` | 按来源筛选 | 来源文章列表 (分页) |
| `/articles/feed/[slug]` | **V4 主菜单子类** (2026-08-07) | 按源分类过滤 (如 finance-macro/tech-ai), `/news?menu={slug}` |
| `/articles/list` | 全部文章 | 分页 20/页、排序下拉 (最新/最热, `?sort=`) |
| `/events` | 事件列表 | 分页 20/页、type/stage/country 筛选 + 排序下拉 (首次/更新/置信度, `?sort=`) |
| `/events/[id]` | 事件 Dossier | 7 面板：Header/Fact/Evidence/Timeline/SourceChain/Intelligence/Graph |
| `/stories` | 故事列表 | **四维度聚合** (Subject/Action/Object/Location 菜单切换, `?dimension=`) + 维度徽章 |
| `/stories/[id]` | 故事时间线 | v2.1: 垂直射线时间线 + 时间点前置标记 + 点击事件就地展开事件内容框(SAO/摘要/证据, 懒加载 EventDossier), 消除时间标记与卡片重叠 |
| `/entities` | 实体中心 | 实体列表(按事件次数排序) + 搜索 |
| `/entities/[name]` | 实体画像 | 国家归属 + 关系网络 + KB 关联 + 相关事件 + 同国实体 + 别名 |
| `/search` | 搜索 | 事件全文搜索 (debounce 300ms, 2 字符起搜) |
| `/sources` | 来源注册表 | 来源权威度柱状图 (实时 event/article 数) |
| `/map` | 地理监控 V2 | MapLibre GL 地图 + 5 区域/6 类型筛选；hover 列表联动地图标记；"All"可显示全部 (≤1000) |
| `/login` | 登录 | JWT 认证 (localStorage) |
| `/admin` | 管理 | 文章/用户/广告统计 + 快捷导航 |
| `/admin/pipeline` | Pipeline 配置 | 评分 JSON + 聚合阈值编辑 |
| `/admin/sources` | 来源管理 | 可排序表格 (等级 S/A/B/C/D + **评分** 0-20 + 文章窗口 + 失败/状态 + 搜索) |
| `/admin/status` | Pipeline 状态 | KPI + 事件阶段分布 + 文章 Tier 分布 + 最近活动 |
| `/config` | 配置中心 | 14 Tab: RSS参数/Pipeline/AI增强/评分/聚合/抓取/源列表/域名/状态/事件校对/实体管理/实体关系/数据模型/**故事管理** |

## API 调用方式

所有前端页面通过统一的 `/api/v1/*` 前缀调用后端 API：

```typescript
// lib/api.ts — 统一 API 客户端
async function fetchAPI<T>(path: string): Promise<T> {
  const res = await fetch(`/api/v1${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

Nginx 反向代理将 `/api/v1/*` 路由到 FastAPI 后端容器 (:8000)。

## 认证系统

```typescript
// lib/auth.tsx — React Context
// JWT Token 存储在 localStorage
// 登录 → POST /auth/login → {token, level}
// useAuth() hook: { user, login, logout, isAdmin, isVip }
```

用户等级: `free` (公开内容) · `vip` (全文) · `admin` (管理后台)

## 前端状态管理

- **无全局状态管理库** — 页面级 React state (useState/useEffect)
- **Auth** — React Context + localStorage 存储 JWT
- **路由** — Next.js App Router + `useSearchParams` 参数驱动筛选

## 样式系统

- **Tailwind CSS v4** — 通过 `@tailwindcss/postcss` 集成
- **shadcn/ui** — 基础 UI 组件 (button)
- **CSS 变量** — 全局样式在 `globals.css`
- **深色/浅色** — 通过 CSS 变量 `--background` / `--foreground` 切换

## 关键依赖

| 包 | 版本 | 用途 |
|---|:----:|------|
| next | 16.2.10 | 框架 |
| react / react-dom | 19.2.4 | UI 库 |
| maplibre-gl | ^5.24.0 | 世界地图 |
| react-simple-maps | ^3.0.0 | 简易地图 (备用) |
| d3 | ^7.9.0 | 数据可视化 (热度图) |
| lucide-react | ^1.24.0 | 图标 |
| date-fns | ^4.4.0 | 日期格式化 |
| class-variance-authority | ^0.7.1 | 组件变体管理 |

## Docker 构建

```dockerfile
FROM node:20-alpine
# Next.js 16 standalone output
ENV NEXT_PUBLIC_API_URL=/api/v1
CMD ["npm", "exec", "next", "start", "-p", "3000"]
```
