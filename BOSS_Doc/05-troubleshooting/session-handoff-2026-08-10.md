# 会话交接 2026-08-10 — Fact Schema V2 / P1 提取层收尾 / 下一阶段

> 目的: 供下次新建会话读取, 接续工作。关联: ISS-20260810-012 · `references/fact-schema-v2.md`(仓库) · `05-troubleshooting/fact-extraction-p1-review.md`

---

## 一、会话目标(已完成)
P0→P1 Fact 提取层: **契约冻结 + 结构正确性(错误Fact=0)+ 收尾**, 不追模型精度天花板。

## 二、已完成(代码已提交)

### P0 Fact Schema V2(契约冻结)
- `references/fact-schema-v2.md`(search-engine-v2 仓库): facts[] / action{type,status,polarity} / object_type / evidence_type(枚举含 UNKNOWN)+ P0 三门槛(Gate1结构/Gate2 eligibility/Gate3 精度baseline)+ 生产提取方案冻结。
- canonicalizer: 值/短语实体化门控(no ENT_ 垃圾) + action 词表扩充 + status/polarity。
- fact_pipeline: facts[](可空) + 结构化 payload + C-tier RuleFactEngine 接口。
- fact_validator.py: PASS/REPAIR/REJECT(不重新推理)。
- aggregator: 只消费 PASS/REPAIR facts(best-fact)。
- Event Relevance Filter(fact_eligibility.py): 英中 NON_EVENT 分析过滤。
- 后端: fact 表新列 + news_intelligence.facts_json。

### P1(2026-08-10 CLOSED)
- 模型路由: CJK→Qwen(qwen3-1.7b)中文prompt / 英文→Gemma(gemma-4-e2b-it)英文prompt。
- Context B: 标题+摘要+正文前4段; max_tokens 1500; 每模型信号量 ≤3(ThreadPoolExecutor 6)。
- 中文 eligibility 最小修复(分析/综述/修辞/媒体评论→NON_EVENT)。
- 中文 Golden Set 扩到 20 篇(5 真实 + 15 手写)。
- **P1 FACT CLOSE 验收通过**: 70篇(50英+20中) **错误Fact进聚合=0**, 结构正确, 精度 baseline 总体 S60/A50/O52/T48/L47。

## 三、当前状态
- **生产部署待定**: 代码已提交 search-engine-v2 仓库, **未 sync 生产 profile / VPS**(下轮生产 pipeline 仍用旧代码)。
- 基准: 逐篇并行是生产方案; `extract_batch` 留实验(质量降)。

## 四、遗留任务(下次会话续作)

| 优先级 | 任务 | 说明 |
|---|---|---|
| ✅ | **Entity Grounding 最小版**(#38) | 已做(`34b4b31`): KB→id / miss→Candidate |
| ✅ | **A/B Event Aggregator + 生产接入 + Web验证**(#39) | 已做(`c848656`/`e1938b5`/`1667c6d`): pipeline落库+推VPS → /api/v1/ab-events → /ab-events页; **Web 测试数据已验证, 真实数据待下轮 pipeline** |
| 🟠 | **fact 表新列 ALTER**: VPS `ALTER TABLE fact ADD COLUMN subject_name/object_name/action_status/action_polarity/evidence` | A/B 已部署, 但 fact 表新列未 ALTER(旧 fact 无新列) |
| 🟠 | **下轮 pipeline 验证真实 A/B**: 跑一轮生产 fact_pipeline → curl /api/v1/ab-events 看真实 B/A | 确认生产自动推 A/B |
| 🟡 | 精度长期指标(90/85/85/90/90) | 降为长期优化, 非阻塞 |
| 🟡 | P1-2~P1-7(grounding/action语义/Time-Loc归一/confidence/C-tier) | 并入下一阶段按需做 |

## 五、关键决策(冻结,勿改)
1. **生产提取方案**: 逐篇并行 + 路由(CJK→Qwen/Gemma) + Context B + max_tokens1500 + 每模型信号量3; **不用 extract_batch**。
2. **不换云模型** / **不追90/85** / **不加线程**(LM Studio 并发≈串行 0.88×)。
3. **错误Fact进聚合=0** 是硬门槛, FAIL 不进入后续阶段。
4. 契约唯一真相源: `references/fact-schema-v2.md`(schema 变化必须先改它)。

## 六、续作指引
- **模型**: 本地 LM Studio :1234(qwen3-1.7b-instruct / gemma-4-e2b-it)。
- **测试脚本**(仓库 scripts/prompts/): golden_set_50.json(英) / golden_set_zh.json(中20) / eval_golden.py / bench_router.py / bench_lang.py / bench_close.py。
- **命令**: 跑验证 `cd scripts && python prompts/bench_close.py`; 部署 `python scripts/sync_profile.py --apply`。
- **数据库**: 生产 news_intel.db 路径 `~/AppData/Local/hermes/profiles/outside-deepdeek/skills/research/search-engine-v2/scripts/news_intel/news_intel.db`。
- **文档**: 审查报告 `05-troubleshooting/fact-extraction-p1-review.md`(规则/现状/问题/建议/决策点)。
