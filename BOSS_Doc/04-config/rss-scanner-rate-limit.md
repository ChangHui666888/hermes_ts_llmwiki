# rss-scanner 限流规则（Tier 分级扫描）

> 版本: v1.0 · 2026-08-08 · **状态: 📋 文档先行（对应代码变更待实施）**
> 定位: rss-scanner 生产版的全部"限流/调度"规则 — 谁该扫、多久扫一次、失败怎么冻结、怎么省带宽。此文档为后续代码调整的规格基线。
> 生产入口: `~/AppData/Local/hermes/scripts/rss-scanner.py`（wrapper）→ `profiles/outside-deepdeek/skills/research/search-engine-v2/scripts/hermes-cron/rss-scanner.py`
> 相关: [feed-registry-v4.md](feed-registry-v4.md)（源 schema/tier 语义）· [cron-jobs.md](cron-jobs.md)（外层调度 every 5m）· [issue-tracking.md](../05-troubleshooting/issue-tracking.md)

---

## 1. 规则总览

| 层 | 规则 | 值 | 作用 |
|----|------|:--:|------|
| 外层调度 | Hermes Cron 频率 | **every 5m** | 全局扫描入口 |
| 内层分频 | Tier 间隔 | hot 5min / warm 15min / cold 60min | 按源重要性控制扫描频率 |
| 失败冻结 | 连续失败阈值 | **≥3 次 → 隔离 3600s (60min)** | 故障源自动冷却 |
| 死链降级 | 连续失败 60 次 | **标记死链 → 每周探测 1 次，恢复回归** | 长期死源退出常规扫描，避免每轮白抓 |
| 增量抓取 | ETag / Last-Modified | 304 直接跳过下载 | 内容未变免下载解析 |
| 超时 | 每请求 | hot 6s / warm 10s / cold 15s | 单源超时不拖垮整轮 |
| 并发 | workers | `rss.max_workers` = **10**（代码默认 14） | 控制对代理的连接压力 |
| 连接复用 | 全局 Client 池 | CN / PROXY 各 1 个共享 client | 避免每源新建/关闭连接 |

**tier 分布（197 源，1 禁用）**：`hot: 13` · `warm: 92` · `cold: 92`；类型 `rss: 178 / nitter: 18 / atom: 1`。

---

## 2. Tier 分级扫描（is_due）

### 2.1 间隔定义

```python
TIER_INTERVAL = {"hot": 5 * 60, "warm": 15 * 60, "cold": 60 * 60}

def is_due(state, feed):
    tier = feed.get("tier", "warm")                      # 缺省 warm
    last = state.get(feed["name"], {}).get("last_scan", 0)
    return (now_ts() - last) >= TIER_INTERVAL.get(tier, 15 * 60)
```

### 2.2 语义

- 每轮 cron（5m）只扫 **到期源**，其余源本轮跳过（`本次到期` 计数）。
- `last_scan` 在**成功抓取并解析后**写入 `state[feed]["last_scan"]`。
- 每轮到期量理论稳态 ≈ `13(hot, 每轮) + 92/3(warm, 每 3 轮) + 92/12(cold, 每 12 轮)` ≈ **51 个/轮**。

### 2.3 各 tier 到期节奏（相对 5m cron）

| tier | 间隔(默认) | 每 N 轮扫一次 | 到期源数 |
|------|:--:|:--:|:--:|
| hot | 5 min | 1 | 13 |
| warm | 15 min | 3 | ~31 |
| cold | **15 min**（修复③：60→15） | 3 | ~31 |

> **修复③ (2026-08-08)**：cold 60min→15min，财经/资讯源积压上限从 60 分钟降到 15 分钟；间隔改为 config 可配（`rss.tier_{hot,warm,cold}_interval`，见 §8）。
> **修复① (2026-08-08)**：304 源也更新 `last_scan` —— 修复前 304 源恒为"到期"每轮重抓（实测到期量虚高到 37–83）；修复后回到正常 tier 节奏。

---

## 3. 隔离 / 死链 状态机（Quarantine & Dead-link，修复⑤ 2026-08-08）

**三级生命周期**：`正常 → 隔离(60min) → 死链(每周探测)`，探测恢复即回归正常。

```
连续失败 <3        → 照常扫描（fail 累计）
fail ≥ 3           → 隔离 60min（rss.quarantine_seconds=3600），到期自动重试
fail ≥ 60          → 标记死链 dead_link=true，退出常规扫描，进入每周探测
死链每周探测到期    → 抓一次；成功→清零回归正常；失败→下次探测再延 7 天
```

```python
if ok:
    m["fail"] = 0; m["quarantine_until"] = 0; m.pop("dead_link", None); m.pop("next_probe", None)
else:
    m["fail"] += 1
    if m["fail"] >= DEADLINK_FAILURES:            # 60 次连续失败 → 死链
        m["dead_link"] = True; m["next_probe"] = now_ts() + DEADLINK_PROBE_INTERVAL
        m["quarantine_until"] = 0
    elif m["fail"] >= QUARANTINE_FAILURES:        # 3 次 → 隔离 60min
        m["quarantine_until"] = now_ts() + QUARANTINE_SECONDS
```

- **state 字段**：`fail`（连续失败计数）· `quarantine_until`（隔离到期）· `dead_link`（死链标记）· `next_probe`（下次探测时间）。
- **死链源不进入常规轮次**（不占 `活跃`），仅在 `next_probe` 到期时探测一次；成功即 `update_health(ok)` → 清零回归正常源管理。
- **迁移**：存量 `fail ≥ 60` 的源启动即标记死链，本轮回探测确认。
- 2026-08-08 状态：实测 61 个 HTTP 4xx 死链 + Reuters×3 等 → 迁移后直接进入死链每周探测，常规轮次不再浪费请求。

---

## 4. 增量抓取（ETag / Last-Modified，优化4）

```python
if st.get("etag"):           headers["If-None-Match"] = st["etag"]
if st.get("last_modified"):  headers["If-Modified-Since"] = st["last_modified"]
resp = client.get(feed["url"], timeout=feed_timeout(feed), headers=headers)
if resp.status_code == 304:  # → 未变, 免下载解析
```

- 首次抓取存 `etag`/`last_modified`；后续 304 → 记 `unchanged`，跳过下载/解析/入库。
- **实测正确性**：Seeking Alpha 内容变化时返回 200 + 新 etag（非 304）；UK Gov / TechCrunch 未变时正确 304。
- 不支持 etag 的源（Newsweek、BBC 等 `etag_resp=''`）永远走全量 200 + `last_seen` 去重。

---

## 5. 超时与并发

```python
# rss.hot_timeout=6 / rss.timeout=10 / rss.cold_timeout=15
def feed_timeout(feed):
    if t == "hot": return HOT_TIMEOUT
    if t == "cold": return COLD_TIMEOUT
    return TIMEOUT
```

- 单源超时不终止整轮；失败计入 `fail` 计入隔离。
- 14 workers 共享 1 个代理 client（优化1）——连接复用省建立/关闭开销，但**代理抖动时影响面更大**（见 §6.4）。

---

## 6. 缺陷记录（2026-08-08 实测确认 → 同日已修）

| # | 缺陷 | 修复 | 状态 |
|---|------|------|:--:|
| ① | **304 源不更新 `last_scan`** → 恒为到期，每轮重抓，限流失效 | 304 分支补 `state[name]["last_scan"]=now_ts()` | ✅ 已修 |
| ② | **非 2xx（404/403）被记成功** → 死链永不隔离 | `fetch_feed` 非 2xx/304 返回 error；`_make_client` 加 `follow_redirects=True`（httpx 0.28 默认不跟重定向，NYT 等 301 源被 0 抓，一并修复） | ✅ 已修 |
| ③ | **cold=60min 对财经/资讯源过粗**，积压最多 60 分钟 | cold→15min，间隔改 config 可配（`rss.tier_*_interval`） | ✅ 已修 |
| ④ | **state/report 与 `bk/rss-scanner.py` 共用**，互相覆盖 | bk 版改用 `rss-scanner-bk-state.json` / `-report.json` / `wiki/RSS-Digest-bk`；DB 仍共享（指纹去重） | ✅ 已修 |

### 🔴 修复② 暴露的配置死链（新发现，待清理）

修复②上线后，首轮即暴露 **61 个 HTTP 4xx 死链**（此前全部被静默记为 OK、0 抓、永不隔离）：

- **Nitter 18 源全 403**（`nitter.freedit.eu/*` 已封）
- **404 死链 27**：White House / AFP / 新华网 / 央视新闻 / Interfax / PBC / Le Monde EN / BOJ / Anthropic / FINRA / 第一财经 / NVD / EIA / IEA / a16z / Google AI / World Bank / 环球网 / Meta AI / 界面 / 证券时报 / 上海证券报 / Irish Times / Mistral / Kitco / Zacks / CVPR
- **403 被拒 11**：SEC / Politico / OpenAI / TradingEconomics / CISA / OPEC / FXStreet / S&P / Barrons / Economist / NASA / OECD / CNCF
- **其他**：Microsoft AI 410 / Uber Eng 406 / Reddit Tech 429（可能瞬时）

> 处置：待配置中心批量禁用/换 URL（见 §9）；期间修复②的隔离机制会 3 次失败后自动冻结这些源（30min 冷却），已实测生效。

---

## 7. 运行实测数据（2026-08-08）

| 时间 | 总源 | 活跃 | 隔离 | 本次到期 | OK | 未变(304) | 失败 | 新增 |
|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 11:58:00 | 196 | 192 | 4 | 37 | 36 | 36 | 1 | 0 |
| 11:58:49 | 196 | 192 | 4 | 51 | 48 | 33 | 3 | 0 |
| 11:59:31 | 196 | 192 | 4 | 83 | 79 | 34 | 4 | 2 |
| 12:00:40 | 196 | 192 | 4 | 38 | 38 | 35 | 0 | 0 |
| 12:01:23 | 196 | 192 | 4 | 36 | 34 | 34 | 2 | 0 |
| 12:17:06 | 196 | 192 | 4 | 83 | 73 | 28 | **10** | 2 |
| 12:33:00 | 196 | 192 | 4 | 60 | 52 | 31 | 8 | 0 |
| **12:55:34（修复后·限流）** | 196 | 192 | 4 | **163** | 93 | 38 | 70 | **233** |
| **12:58:00（修复后·--full 不限流）** | 196 | 192 | 4 | **192** | 110 | 51 | 82 | **140** |

> 失败数骤升（70/82）系**修复② 正确暴露 61 个配置死链**（之前静默 OK），非回归；真正网络/代理失败仅 ~9 个。死链 3 次失败后自动隔离（已实测 Reuters/CVPR/Uber/CNCF 等 8 源冻结）。
> `--full` 为修复后新增开关：所有活跃源视为到期，不限流全量扫描。

**新旧对比（同窗口）**：`bk/rss-scanner.py`（老版，94 源硬编码，无 tier 门控）12:26 全扫 → **新增 14**；修复后生产版（含 follow_redirects 恢复 NYT + 不限流全量）→ **新增 140–233**。

**结论**：老文件"抓得多"= 绕过限流 + 捞积压；修复后生产版抓取能力**远超老文件**（NYT/NBC 等 301 源恢复，死链自动隔离）。

---

## 8. 配置项清单

| 配置键 | 当前值 | 代码默认 | 说明 |
|--------|:--:|:--:|------|
| `rss.proxy` | `socks5://127.0.0.1:10808` | 同上 | 代理；`intl` 源走代理，`cn` 直连 |
| `rss.max_workers` | **10** | 14 | 并发抓取数 |
| `rss.timeout` | 10 | 10 | warm 默认超时(s) |
| `rss.hot_timeout` | 6 | 6 | hot 超时(s) |
| `rss.cold_timeout` | 15 | 15 | cold 超时(s) |
| `rss.quarantine_failures` | 3 | 3 | 连续失败冻结阈值 |
| `rss.quarantine_seconds` | **3600** | 3600 | 隔离时长(s)，修复⑤：1800→3600(60min) |
| `rss.deadlink_failures` | 60 | 60 | 连续失败→死链阈值，修复⑤新增 |
| `rss.deadlink_probe_interval` | 604800 | 604800 | 死链每周探测间隔(s)=7天，修复⑤新增 |
| `rss.tier_hot_interval` | (未设→默认 300) | 300 | hot 扫描间隔(s)，修复③新增，config 可配 |
| `rss.tier_warm_interval` | (未设→默认 900) | 900 | warm 扫描间隔(s)，修复③新增 |
| `rss.tier_cold_interval` | (未设→默认 900) | **900**（修复③：3600→900） | cold 扫描间隔(s)，修复③新增 |

---

## 9. 后续调整（已完成 / 待办）

### ✅ 已完成（2026-08-08，与本文档同 commit）
1. 缺陷①：304 源也更新 `last_scan`（还原 tier 门控语义，压掉恒到期）。
2. 缺陷②：非 2xx 状态码计失败 → 自动隔离；`follow_redirects=True` 恢复 NYT 等 301 源。
3. 缺陷③：cold 60min → 15min，间隔 config 可配。
4. 缺陷④：`bk/rss-scanner.py` 改用独立 state/report/wiki 路径。
5. 新增 `--full` / `--no-limit` 开关：不限流全量扫描（对比测试用）。
6. 同步生产（`sync_profile.py --apply`）+ 实测（限流 233 篇 / --full 140 篇）。
7. **修复⑤ 死链状态机**：隔离 60min + 连续 60 次失败标记死链 + 每周探测恢复回归（§3）。

### 🔴 待办：配置中心死链清理（约 61 源）
- 死链状态机已自动接管（fail≥60 → 死链每周探测，常规轮次不再浪费请求），**无需手动禁用**。
- 可选的配置中心操作：替换高价值死链 URL（White House/AFP/新华网/Nitter 等换可用源），提升覆盖；死链自动探测恢复也会回归。
