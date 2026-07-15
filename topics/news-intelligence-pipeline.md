# News Intelligence Pipeline — 运维手册

> 自动抓取流水线：CRON 定时任务 + 抓取引擎 + 聚合 → 云端部署

## 定时任务

### auto-pipeline（主流水线）

| 字段 | 值 |
|------|-----|
| **任务名** | `auto-pipeline` |
| **脚本** | `auto-pipeline.py` |
| **调度** | 每 15 分钟 |
| **模式** | `no_agent=true`（零 LLM 成本） |
| **Cron 文件** | `~/.hermes/profiles/outside-deepdeek/cron/jobs.json` |

**Pipeline 6 步骤级联：**

```
Step 1: Sync + Score (无内容文章纳入打分)
Step 2: RSS FullText (HTML密度<30%直接提取，cost=0)
Step 3: FETCH (batch.py 批量抓取)
  3a: SearXNG Recovery (score 80-89，免费替代URL)
  3b: Tavily Recovery (score ≥90，付费AI摘要)
Step 4: Aggregate (SAO事件聚类)
Step 5: Cloud Sync (推送事件到PG)
Step 6: Content Push (文章内容推送到PG)
```

## 创建命令

```bash
# 在 Hermes 对话中执行（/cron 命令）：
/cron create auto-pipeline --script auto-pipeline.py \
  --schedule "once in 15m" --repeat forever \
  --no-agent --deliver local

# 或通过 CLI：
hermes cron create auto-pipeline \
  --script auto-pipeline.py \
  --schedule "once in 15m" \
  --repeat forever \
  --no-agent \
  --deliver local
```

## 维护命令

```bash
# 查看所有定时任务
hermes cron list

# 查看任务详情
hermes cron show auto-pipeline

# 启用/禁用
hermes cron enable auto-pipeline
hermes cron disable auto-pipeline

# 立即手动触发一次
hermes cron run auto-pipeline

# 修改调度周期
hermes cron update auto-pipeline --schedule "once in 10m"

# 删除任务
hermes cron delete auto-pipeline

# 查看执行日志
hermes cron log auto-pipeline
```

## 手动运维命令

```bash
cd /c/Users/ChangHui/AppData/Local/hermes/profiles/outside-deepdeek/skills/research/search-engine-v2/scripts

# 完整 Pipeline 运行
python auto-pipeline.py

# 仅查看状态（不抓取）
python news_intel/pipeline_check.py check

# 仅运行抓取（batch.py）
python batch.py 2>&1 | tee batch.log

# 仅运行聚合
python -m news_intel.aggregator

# 推送事件到云端
python cron-sync.py

# RSS 扫描器状态
python -c "
from rss_scanner import get_scanner_status
import json; print(json.dumps(get_scanner_status(), indent=2))
"
```

## 关键路径

| 组件 | 路径 |
|------|------|
| Cron 配置 | `~/.hermes/profiles/outside-deepdeek/cron/jobs.json` |
| Pipeline 脚本 | `.../search-engine-v2/scripts/auto-pipeline.py` |
| Pipeline 日志 | `.../search-engine-v2/scripts/pipeline.log` |
| SQLite DB | `.../search-engine-v2/scripts/news_intel/news_intel.db` |
| 抓取器 | `.../search-engine-v2/scripts/core/fetchers.py` |
| 聚合器 | `.../search-engine-v2/scripts/news_intel/aggregator.py` |
| 云同步 | `.../search-engine-v2/scripts/cron-sync.py` |
| 健康检查 | `.../search-engine-v2/scripts/news_intel/pipeline_check.py` |

## 云端部署

| 组件 | 地址 |
|------|------|
| 前端 | `http://100.107.117.23` |
| API | `http://100.107.117.23/api` |
| PG Admin | `http://100.107.117.23:5050` (pgAdmin) |
| SearXNG | `http://100.107.117.23:8080` |

```bash
# 云端 SSH
ssh administrator@100.107.117.23   # root123root!@

# 重载后端 API
ssh administrator@100.107.117.23 'cd /home/administrator/news-platform-v8 && docker compose up -d --build backend'

# 查看容器状态
ssh administrator@100.107.117.23 'cd /home/administrator/news-platform-v8 && docker compose ps'

# 查看 PG 日志
ssh administrator@100.107.117.23 'docker logs news-platform-v8-postgres-1 --tail 20'

# 连接 PG
ssh administrator@100.107.117.23 "docker exec -it news-platform-v8-postgres-1 psql -U admin -d news_intel_db"
```

## 抓取策略级联

```
RSS FullText (cost=0) → Direct (cost=1) → Archive (cost=1)
→ Scrapling (cost=2) → [失败,score 80-89] SearXNG (cost=2)
→ [失败,score ≥90] Tavily (cost=5)
```

## 统计查询

```sql
-- 连 PG：查看 RSS 源成功率排行
SELECT source_name, strategy,
       SUM(ok_count) AS ok, SUM(fail_count) AS fail,
       ROUND(SUM(ok_count)*100.0/NULLIF(SUM(ok_count+fail_count),0),1) AS pct
FROM fetch_stats WHERE source_name IS NOT NULL
GROUP BY source_name, strategy ORDER BY SUM(ok_count+fail_count) DESC;
```
