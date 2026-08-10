# Fact 提取层 P1 调优审查报告(规则/现状/问题/建议)

> 状态: 供审视决策 (2026-08-10) · 关联: ISS-20260810-012 · 契约: `references/fact-schema-v2.md`

---

## 一、具体规则(已冻结)

### 1.1 Fact Schema V2(全系统唯一契约)
- 一篇文章 → `facts[]`(0..3 条,可空);每条 `subject/action/object/time/location` 均为**结构化对象** + `confidence/evidence/evidence_type`。
- `action` = `{type, status, polarity, verb}`;**枚举含 `UNKNOWN`**(status 11 值 / polarity 4 值 / object_type 13 值 / evidence_type 10 值)。
- **Object ≠ Entity**:值/金额/日期/短语(`$0.22`/`81st anniversary`/`AI chip fears ease`)不再生成 `ENT_` 临时实体;有 `object_type` 区分。
- 契约唯一真相源: `references/fact-schema-v2.md`(仓库,随代码版本)。

### 1.2 P0 三门槛
| 门槛 | 判定 | 状态 |
|---|---|---|
| Gate1 结构 | Schema valid / Validator crash / REJECT 入聚合 = 100%/0/0 | ✅ PASS |
| Gate2 Eligibility | **错误Event Fact→聚合 = 0** | ⚠️ 部分(英文过,中文漏) |
| Gate3 精度 | 记录 baseline(Qwen-1.7B 天花板), 不单独卡 PASS; 90/85/85/90/90 由 P1 | 📊 baseline |

### 1.3 生产提取方案(2026-08-10 冻结)
```
逐篇并行(非批量): main() ThreadPoolExecutor(6) + 每模型 BoundedSemaphore(3)
  CJK → Qwen(qwen3-1.7b) + 中文 FACT_PROMPT
  英文 → Gemma(gemma-4-e2b-it) + 英文 FACT_PROMPT_EN
  Context B: 标题 + 摘要 + 正文前4段
  max_tokens = 1500 (SAO 不截断)
extract_batch(results[] 紧凑) = 实验选项, 不接生产
```

### 1.4 硬门槛
- **错误 Fact 进聚合 = 0**(架构正确性,非模型精度)——FAIL 则不进入 P1/P2/P3。

---

## 二、现状(已完成 + 数据)

### 2.1 P0(代码 + 门禁)
- Schema V2 + canonicalizer 门控 + fact_validator(PASS/REPAIR/REJECT)+ aggregator 只消费 PASS/REPAIR + Event Relevance Filter + Golden Set 50 字段级验收。
- **Gate1+2 部分通过**:Golden Set 50(全英文)错误Fact=0;加入中文后错误Fact=1-2。

### 2.2 P1 进展
- **模型路由**(中文Qwen/英文Gemma)+ 语言 prompt + Context B + 并发控制(每模型≤3)+ max_tokens 1500。
- `extract_batch` 实验(结果[] 批量)。

### 2.3 基准数据
| 方案 | Subject | Action | Object | Time | Location | 效率 |
|---|---|---|---|---|---|---|
| 逐篇并行(英文, Context B) | 64% | 49% | 51% | 47% | 40% | ~91s/批均 |
| 逐篇并行(中文, Context B) | 33% | 67% | 33% | 67% | 100% | 5/5 成功 |
| extract_batch(55篇混合) | 44% | 38% | 38% | 23% | 19% | 155s(3×快) |
| 并发 vs 串行 | — | — | — | — | — | 0.88×(无并行) |

---

## 三、问题(需决策)

### P-1 🔴 错误Fact进聚合 > 0(硬门槛违反)
- 定位: **中文 eligibility 过滤器不足** —— 中文分析/综述(如"中东动荡""德语媒体")未命中英文 NON_EVENT 模式 → 仍产 Fact。
- 影响: 违反 Gate2 硬门槛, 阻塞 P1/P2/P3。
- 建议: 补中文 NON_EVENT 关键词(分析/观点/综述/解读)。

### P-2 🔴 字段精度受 Qwen-1.7B 天花板
- 现状: Subject~69 / Action~47 / Object~51(远低于 90/85/85)。
- 影响: Gate3 精度目标无法在 Qwen-1.7B 达成。
- 建议: ①P1 各项叠加(语义/归一/grounding)看提升; ②更强模型(DeepSeek 推理慢, 需非推理/云模型)做模型上限实验。

### P-3 🟠 Action 精度低(陈述动词 canonicalization 不足)
- 现状: 大量 "says/claims/insists/vows" 类动词映射不稳, OTHER 占比高。
- 建议: P1-3 Action 语义归一(verb+negation+modal+status 联合)。

### P-4 🟠 Time/Location 未规则归一
- 现状: T~44 / L~40(依赖 LLM, 不干净)。
- 建议: P1-4/5 LLM 候选 + 规则归一(Friday+published_at→日期;unknown→null)。

### P-5 🟡 extract_batch 质量降(已回退)
- 现状: 提速 3× 但 S44(紧凑 prompt 丢 location/time, facts覆盖减半)。
- 建议: 留实验; 生产用逐篇并行。

### P-6 🟡 并发无增益
- 现状: LM Studio 并发≈串行(0.88×), 3 线程只是占槽非并行。
- 建议: 不加线程; 每模型限 3 防过载即可。

### P-7 🟡 中文样本少
- 现状: 仅 5 篇中文, 统计意义有限。
- 建议: 扩充中文 Golden Set(≥20 篇)以可靠统计中文准确率。

---

## 四、建议(供决策)

| # | 建议 | 优先级 | 理由 |
|---|---|---|---|
| S1 | **补中文 eligibility 模式**(分析/综述/观点关键词) | 🔴 P0 | 拉回 错误Fact=0 硬门槛, 阻塞后续 |
| S2 | **P1-3 Action 语义归一**(verb+negation+modal+status) | 🟠 P1 | 提升 Action 精度(当前最低) |
| S3 | **P1-4/5 Time/Location 规则归一** | 🟠 P1 | LLM候选+规则, 提升 T/L |
| S4 | **扩充中文 Golden Set**(≥20 篇) | 🟡 P1 | 可靠统计中文准确率 |
| S5 | **模型上限实验**(非推理云模型跑 Golden Set) | 🟡 P1 | 决定是否需换模型达标 90/85 |
| S6 | **生产部署时机**: 待 S1(硬门槛)完成后 | 🟠 P2 | 结构正确性优先于精度 |
| S7 | extract_batch 留实验, 生产逐篇 | ✅ 已冻结 | 批量质量降, 已回退 |

---

## 五、决策点(请拍板)

1. **S1 中文 eligibility**: 是否立即补(拉回硬门槛)?
2. **精度目标路径**: 靠 P1 各项叠加(Qwen) 还是 换更强模型(云)?
3. **生产部署**: 待 S1 后部署, 还是 P1 全部完成后一次部署?
4. **中文 Golden Set**: 是否扩到 20+ 篇再统计?
