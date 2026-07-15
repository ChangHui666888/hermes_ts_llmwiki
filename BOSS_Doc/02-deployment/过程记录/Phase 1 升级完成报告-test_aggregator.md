

## Phase 1 升级完成报告

### 执行概况

```
Batch 1 (P0): 3/3 ✅   Schema冻结 + Entity ID + Action detail
Batch 2 (P1): 3/3 ✅   Lifecycle + Confidence + Summary
Batch 3 (P2): 1/2 ⏸   首发识别 ✅ | 实时雷达(需持久化) 延后
──────────────────────────────────
完成: 7/8 | 耗时: ~30min | 提交: b5464d0
```

### 冻结的 Event Schema (21字段)

```json
{
  "event_id": "EVT-20260710-006",
  "subject":    {"name": "Apple", "type": "Company"},
  "action":     {"type": "SUES", "detail": "OpenAI over stealing trade secrets"},
  "object":     {"name": "OpenAI", "type": "Company"},
  "event_type": "Legal",
  "event_time": "2026-07-10T00:00:00",
  "location":   {"country": null, "region": null},
  "source":     {"primary_source": "DW News", "authority": 16, "source_count": 8, "sources": [...]},
  "doc_refs":   [{"url": "...", "title": "..."}],
  "actors":     [{"entity": "Apple", "type": "Company", "role": "Initiator"}, ...],
  "title":      "Apple calls OpenAI's hardware business...",
  "summary":    "Apple has accused the company behind ChatGPT...",
  "keywords":   ["Legal", "Technology"],
  "confidence": 0.89, "coherence": 95.7,
  "extraction_method": "v4.3-saeo",
  "related_entities": [{"name":"Apple","type":"Company"}, ...],
  "article_count": 8, "article_ids": [...],
  "stage":      "active",
  "first_seen": "2026-07-10T00:00:00",
  "last_updated": "2026-07-11T00:00:00"
}
```

### 验证命令

```bash
# 查看新 schema
python test_aggregator.py --hours 24 --window 6 --limit 10 --single 1

# 批量对比
python test_aggregator.py --hours 24 --window 6 --limit 100
```

### 未完成项

| 任务 | 原因 | 建议 |
|------|------|------|
| 3.2 实时雷达 | 需要事件持久化到文件/DB才能对比"新增/更新" | 后续建 `~/.hermes/event-snapshot.json` |