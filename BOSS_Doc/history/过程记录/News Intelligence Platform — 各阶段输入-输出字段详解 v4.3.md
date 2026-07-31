

---

## 产出

[各阶段输入/输出字段详解](<C:/Users/ChangHui/AppData/Local/hermes/profiles/outside-deepdeek/skills/research/search-engine-v2/scripts/news_intel/io-fields.html>)

### 6 份产出物汇总

| # | 文件 | 内容 |
|:--:|------|------|
| 1 | `architecture.html` | 5层宏观架构图 (Layer 0→5) |
| 2 | `detail-flow.html` | **详细业务流程图** — 双模式 + 依赖标注 |
| 3 | `io-fields.html` | **输入输出字段逐表追踪** — 本次新增 |
| 4 | `SCHEMA.md` | 21字段完整 JSON Schema + 置信度公式 + Action枚举 |
| 5 | `aggregator.py` | 606行可运行实现 |
| 6 | `test_aggregator.py` | 验证: `--hours 24 --window 6 --single N` |

### IO 追踪速览

```
Phase 0: cron → (无数据)
Phase 1: rss-archive.db {source,title,summary,link,category,date}
         → score_article() → {total,source,impact,entity,market,velocity,tier,entities,categories}
         → news_intel.db 三表 (rss_raw=18, intel=14, content=19 field)
Phase 2: batch.py {url[]} → {ok,url,domain,content,strategy_used,total_cost,cost_trace,structured,temporal_check}
         → news_content填充
Phase 3: 三表JOIN → build_fingerprint {subject,action,object,event_type,topic,country,participants}
         → cluster → 21字段 Event Object
Phase 4: 可选 LLM 增强 (tags, entities, summary, market_signal, risk_level)
Phase 5: pusher.py → POST /internal/news/batch (17 field per article)
```