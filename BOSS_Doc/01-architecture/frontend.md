# 前端 — Sentinel Intelligence (Next.js 16)

> 最后更新: 2026-07-29
> 技术栈: Next.js 16.2.10 · React 19.2.4 · TypeScript 5.9 · Tailwind CSS v4 · shadcn/ui
> 部署: Docker 容器 (`news-platform-v8-frontend-1`, `node:20-alpine`)
> 网络: **仅 Tailscale 内网 (100.107.117.23)，非公网服务**

## 架构概览

```
frontend/src/
├── app/                   # Next.js App Router 页面
│   ├── layout.tsx         # 全局布局 (Header + Sidebar + AuthProvider)
│   ├── globals.css        # Tailwind v4 全局样式
│   ├── page.tsx           # 首页: Situation Dashboard
│   ├── articles/          # 文章模块 (纽约时报中文网风格)
│   │   ├── page.tsx       # 新闻中心 (头条+来源分组+分类)
│   │   ├── [id]/page.tsx  # 文章详情 (VIP自动全文)
│   │   ├── category/[name]/page.tsx  # 分类筛选
│   │   ├── source/[name]/page.tsx    # 按来源筛选 (分页)
│   │   └── list/page.tsx             # 全部文章 (分页)
│   ├── events/            # 事件模块
│   │   ├── page.tsx       # 事件列表 (筛选/分页)
│   │   └── [id]/page.tsx  # 事件 Dossier 详情 (7 个子组件)
│   ├── entities/[name]/page.tsx  # 实体画像 (国家+关联+事件)
│   ├── search/page.tsx    # 全局搜索 (debounce 300ms)
│   ├── sources/page.tsx   # 来源注册表
│   ├── map/page.tsx       # 地理监控 (MapLibre GL, 195国坐标)
│   ├── login/page.tsx     # 登录页
│   ├── admin/             # 管理后台
│   │   ├── page.tsx       # 管理仪表盘
│   │   ├── sources/page.tsx  # 来源注册表 (可排序表格)
│   │   ├── status/page.tsx   # Pipeline 状态 (运行日志+统计)
│   │   └── pipeline/page.tsx  # Pipeline 配置
│   └── config/page.tsx    # 配置中心 (9 Tab)
├── lib/
│   ├── auth.tsx           # Auth Context (ready状态防竞态)
│   ├── country-coords.ts  # 完整世界国家坐标库 (195国)
│   └── api.ts             # API 客户端
├── components/
│   ├── layout/
│   │   ├── Header.tsx     # 顶栏 (Logo + 搜索 + UTC时钟 + 状态)
│   │   └── Sidebar.tsx    # 侧栏导航 (6 组菜单)
│   ├── dashboard/
│   │   ├── MetricCard.tsx # 指标卡片
│   │   ├── WorldMap.tsx   # 简易世界地图 (react-simple-maps)
│   │   ├── MapLibreWorldMap.tsx  # MapLibre GL 地图 (主版)
│   │   ├── EventHeat.tsx  # 实体热度图
│   │   └── IntelligenceFeed.tsx  # 情报流
│   ├── event/
│   │   ├── EventCard.tsx      # 事件卡片 (首页)
│   │   ├── EventHeader.tsx    # 事件头部 (SAO + 置信度)
│   │   ├── FactPanel.tsx      # 事实面板
│   │   ├── EvidenceCard.tsx   # 证据引用
│   │   ├── Timeline.tsx       # 时间线
│   │   ├── SourceChain.tsx    # 来源链
│   │   ├── RelationGraph.tsx  # 实体关系图 (SVG)
│   │   └── IntelligencePanel.tsx  # LLM 分析面板
│   ├── common/
│   │   └── Badge.tsx      # 通用标签组件
│   └── ui/
│       └── button.tsx     # shadcn 按钮
├── contracts/             # 冻结 API Contract v1.0
│   ├── event.ts           # EventDossier 接口定义 (17 个类型)
│   ├── dashboard.ts       # DashboardResponse 接口
│   └── source.ts          # SourceEntity 接口
└── lib/
    ├── api.ts             # API 客户端 (fetchAPI<T>)
    ├── auth.tsx           # Auth Context (Context + Provider)
    ├── types.ts           # 类型重导出
    └── utils.ts           # 工具函数
```

## 页面路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | Dashboard | 态势感知中心：5 指标、世界地图、Hot Events、热度图、情报流 |
| `/articles` | 文章列表 | Hot(6篇) + Latest(12篇) + 分类标签云 |
| `/articles/[id]` | 文章详情 | VIP/Admin 可见全文 content_md |
| `/articles/category/[name]` | 分类筛选 | 按分类查看文章 |
| `/events` | 事件列表 | 分页 20/页、按 type/stage/country 筛选 |
| `/events/[id]` | 事件 Dossier | 7 面板：Header/Fact/Evidence/Timeline/SourceChain/Intelligence/Graph |
| `/search` | 搜索 | 事件全文搜索 (debounce 300ms, 2 字符起搜) |
| `/sources` | 来源注册表 | 24 来源的权威度柱状图 |
| `/map` | 地理监控 | MapLibre GL 地图 + 5 区域/6 类型筛选 |
| `/login` | 登录 | JWT 认证 |
| `/admin` | 管理 | 文章/用户/广告统计 |
| `/admin/pipeline` | Pipeline 配置 | 键值对配置管理 |

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
