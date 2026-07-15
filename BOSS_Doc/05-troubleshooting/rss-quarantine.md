# RSS 源隔离

## 现象

```
活跃: 0  隔离: 94
⚠️ 所有源被隔离, 检查代理或网络!
```

## 原因

RSS 源连续访问失败 ≥3 次，触发隔离机制。

## 规则（2026-07-10 已调整）

| 项 | 改前 | 改后 |
|------|------|------|
| 失败次数阈值 | 3次 | 3次 |
| 隔离时长 | 24h (86400s) | 30min (1800s) |

文件: `~/.hermes/scripts/rss-scanner.py:255`

```python
if m["fail"] >= 3: m["quarantine_until"] = now_ts() + 1800
```

## 解决

```bash
# 方法1: 删除状态文件（立即恢复）
rm ~/.hermes/rss-scanner-state.json

# 方法2: 等待30分钟自动恢复
```

## Qwen 超时

### 现象

```
[qwen] timed out
[qwen] Client error '400 Bad Request'
```

### 规则（2026-07-10 已调整）

| 项 | 改前 | 改后 |
|------|------|------|
| 超时 | 5s | 30s |

文件: `news_intel/enhancers.py:130`

超时后自动降级为 Python 规则，不影响主流程。
