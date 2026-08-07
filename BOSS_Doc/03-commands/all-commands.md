# 命令速查

## Hermes

```bash
hermes config show
hermes config set model.default deepseek-v4-pro
hermes config set model.provider deepseek
```

## Cron

```powershell
# 创建（注意：必须 "every X" 非 "X"）
hermes cron create "every 5m"  --script "rss-scanner.py"   --no-agent --deliver "local" --name "rss-scanner"
hermes cron create "every 15m" --script "auto-pipeline.py" --no-agent --deliver "local" --name "auto-pipeline"
# config-agent 为后台常驻进程 (60s 轮询 VPS 配置)

# 管理
hermes cron list
hermes cron run <id>
hermes cron remove <id>
```

## RSS

```bash
python ~/.hermes/scripts/rss-scanner.py
sqlite3 ~/.hermes/rss-archive.db "SELECT source,title FROM rss_articles ORDER BY created_at DESC LIMIT 10"
rm ~/.hermes/rss-scanner-state.json       # 重置隔离
cat ~/.hermes/rss-scanner-report.json     # 查看报告
```

## Pipeline

```bash
cd ~/.hermes/scripts
python auto-pipeline.py                   # 手动运行生产 pipeline

# 日志
cat pipeline.log
# PowerShell: Get-Content .\pipeline.log -Tail 50

# 部署 cron 脚本回 Hermes 目录
python scripts/hermes-cron/deploy-cron.py --apply
```

## Docker（云主机）

```bash
ssh administrator@100.107.117.23
cd news-platform-v8
docker compose ps
docker compose up -d
docker compose logs api
```
## 完整使用方法

### 环境

```bash
本地: Windows 11, Python 3.11, git-bash
Hermes: ~/AppData/Local/hermes
云主机: 100.107.117.23 (administrator)
```

---

### 一、Cron 管理

```bash
# 列出所有作业
hermes cron list

# 手动触发
hermes cron run <job_id>

# 删除
hermes cron remove <job_id>

# 暂停/恢复
hermes cron pause <job_id>
hermes cron resume <job_id>
```

**创建命令**：

```powershell
# RSS 扫描 (每5分钟)
hermes cron create "every 5m" --script "rss-scanner.py" --no-agent --deliver "local" --name "rss-scanner"

# 情报生产 Pipeline (每15分钟)
hermes cron create "every 15m" --script "auto-pipeline.py" --no-agent --deliver "local" --name "auto-pipeline"
```

**Windows Task Scheduler**：

```powershell
schtasks /create /tn "Hermes-Git-Backup" /tr "C:\Users\ChangHui\AppData\Local\hermes\scripts\git-backup.sh" /sc daily /st 12:00 /f
schtasks /create /tn "Hermes-Full-Backup" /tr "C:\Users\ChangHui\AppData\Local\hermes\scripts\full-backup.sh" /sc daily /st 18:00 /f
```

---

### 二、RSS

```bash
# 手动运行
python ~/AppData/Local/hermes/scripts/rss-scanner.py

# 查询
sqlite3 ~/.hermes/rss-archive.db "SELECT source,title,date FROM rss_articles ORDER BY created_at DESC LIMIT 10"

# 按分类
sqlite3 ~/.hermes/rss-archive.db "SELECT source,title FROM rss_articles WHERE category='通讯社' LIMIT 10"

# 关键词搜索
sqlite3 ~/.hermes/rss-archive.db "SELECT source,title FROM rss_articles WHERE title LIKE '%Trump%Iran%' LIMIT 10"

# 今日新增
sqlite3 ~/.hermes/rss-archive.db "SELECT COUNT(*) FROM rss_articles WHERE date(created_at)=date('now','localtime')"

# 查看报告
cat ~/.hermes/rss-scanner-report.json

# 重置隔离
rm ~/.hermes/rss-scanner-state.json
```

---

### 三、Pipeline

```bash
cd ~/AppData/Local/hermes/profiles/outside-deepdeek/skills/research/search-engine-v2/scripts

# 生产 pipeline (cron 每15分钟, 手动触发同样命令)
python auto-pipeline.py

# 只评分 (不推送)
python -m news_intel.pipeline --hours 2

# 评分 + 抓全文
python -m news_intel.pipeline --hours 2 --fetch

# 查本地 DB
sqlite3 news_intel/news_intel.db "SELECT tier,COUNT(*) FROM news_intelligence GROUP BY tier"
sqlite3 news_intel/news_intel.db "SELECT extraction_method,COUNT(*) FROM news_content GROUP BY 1"

# 查看日志 (分步统计)
cat pipeline.log
# PowerShell: Get-Content .\pipeline.log -Tail 50
```

---

### 三.5、Fact Layer (L10, Schema V1.0)

```bash
# 手动执行 (⚠️ 需系统 Python311, 有 gliner/transformers/torch; LM Studio Qwen 在线)
C:\Users\ChangHui\AppData\Local\Programs\Python\Python311\python.exe ^
  news_intel/fact_pipeline.py --limit 50 --api http://100.107.117.23 --workers 4 --verbose

# 完整日志到文件
... > fact_run.log 2>&1

# 查 VPS fact 数据
docker exec news-platform-v8-postgres-1 psql -U news_admin -d news_intel -c "SELECT id,article_id,action_type,action_event_type,location FROM fact ORDER BY id DESC LIMIT 10"
docker exec news-platform-v8-postgres-1 psql -U news_admin -d news_intel -c "SELECT fact_id,entity_id,role FROM fact_entity LIMIT 10"
```

参数: `--db` 本地DB(默认profile) / `--limit N` 篇数 / `--api` VPS地址 / `--workers N` 并发线程 / `--verbose` 每篇明细日志
输出: `[load]→[GLiNER]串行→[extract]多线程→[push]→[save]`，推送成功 `{"ok":N,"fail":0}` 即入库。
详细设计: `references/fact-schema-v1.md` + `references/fact-extractor-tuning.md`。

---

### 四、事件聚合 (L8)

```bash
cd ~/AppData/Local/hermes/profiles/outside-deepdeek/skills/research/search-engine-v2/scripts

# 手动验证 (显示事件)
python test_aggregator.py --hours 24 --window 12 --limit 50

# 验证 + 生成 Insight
python test_aggregator.py --hours 24 --window 12 --limit 50 --insight

# Python API
python -c "
from news_intel.aggregator import aggregate_events
from news_intel.generator import generate_for_event
# ... 加载 articles ...
events = aggregate_events(articles, window_hours=6)
for ev in events:
    insight = generate_for_event(ev)
"
```

---

### 五、部署 & API 测试（news-platform-v8）

```bash
cd ~/.hermes-web-ui/coding-agent/workspace/default/global/search-engine-v2/scripts/news-platform-v8

# API 全量测试（实时，连云主机）
python test_api.py

# Mock 模式（离线，无需网络）
python test_api.py --mock

# 指定测试路径
python test_api.py --endpoint /api/v1/dashboard

# 包含管理端 + 内部端点测试
python test_api.py --admin --internal

# 自动部署到云主机
python deploy-vps.py                    # 全部服务
python deploy-vps.py --service backend  # 只重建后端
python deploy-vps.py --check            # 只检查状态
```

### 七、Docker (云主机)

```bash
ssh administrator@100.107.117.23
cd /home/administrator/news-platform-v8

# 启动/停止
docker compose up -d
docker compose down

# 状态
docker compose ps
docker compose logs api --tail 20

# 重建
git pull
docker compose build --no-cache api
docker compose build --no-cache web
docker compose up -d

# 数据库
docker compose exec postgres psql -U news_admin -d news_intel -c "SELECT COUNT(*) FROM articles"
docker compose exec postgres psql -U news_admin -d news_intel -c "\dt"

# API 测试
curl http://localhost/health
curl http://localhost/news
curl http://localhost/news/hot
```

---

### 八、备份

```bash
# 手动 Git 备份
cd ~/AppData/Local/hermes
git add -A && git commit -m "manual backup" && git push

# 手动全量备份
bash ~/AppData/Local/hermes/scripts/full-backup.sh

# 一键恢复
双击 C:\Users\ChangHui\AppData\Local\hermes\scripts\restore.bat
# 两次输入 YES 确认

# 查看备份
ls F:/hermes-backup/

# 日志
cat ~/AppData/Local/hermes/scripts/logs/full-backup.log
cat ~/AppData/Local/hermes/scripts/logs/git-backup.log
```

---

### 九、数据库查询

```bash
# 本地 SQLite
sqlite3 ~/.hermes/rss-archive.db "SELECT source,title FROM rss_articles ORDER BY created_at DESC LIMIT 10"
sqlite3 news_intel/news_intel.db "SELECT tier,COUNT(*),AVG(score_total) FROM news_intelligence GROUP BY tier"
sqlite3 news_intel/news_intel.db "SELECT extraction_method,COUNT(*) FROM news_content GROUP BY 1"

# 云 PostgreSQL
ssh administrator@100.107.117.23
docker compose -f ~/news-platform-v8/docker-compose.yml exec postgres \
  psql -U news_admin -d news_intel -c "SELECT COUNT(*) FROM articles"
```

---

### 十、Web 访问

```
前端:    http://100.107.117.23
API文档: http://100.107.117.23/docs
```

---

### 十一、模型管理

```bash
hermes config show                        # 查看配置
hermes config set model.default deepseek-v4-pro
hermes config set model.provider deepseek
```

---

### 十二、Wiki

```
C:\Users\ChangHui\wiki\BOSS_Doc\
├── README.md                              # 索引
├── 01-architecture/system-architecture.md # 架构+参数
├── 02-deployment/cloud-deploy.md          # 云部署
├── 02-deployment/backup-restore.md        # 备份恢复
├── 03-commands/all-commands.md            # 命令速查
├── 04-config/cron-jobs.md                 # 计划任务
└── 05-troubleshooting/cron-debug.md       # 排障
```