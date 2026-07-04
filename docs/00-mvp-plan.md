# Matcha KOL Scorer — MVP 落地计划

> 版本：v0.1 · 日期：2026-07-04
> 状态：**决策已定版，待 Fork 后进入实现**

本文档记录 2026-07-04 讨论产出的 MVP 全部决策。是本项目实现阶段的**唯一真相源（single source of truth）**。后续如决策变更，直接在本文档 changelog 追加记录。

---

## 1. 项目定位

**一句话**：给品牌方（泛日式甜品/抹茶方向）提供一个能批量评估达人（抖音/小红书）的开源命令行工具。

**服务对象**：中小品牌投放决策者，一次评估几百达人。

**MVP 交付形态**：命令行 + SQLite + HTML/CSV 报告。**不是 SaaS**，个人机房自用/学习/开源。

**商业化路径**：MVP 阶段学习/研究用途；如未来商用需替换爬虫层（走 MediaCrawlerPro 授权 / 官方开放平台 / 第三方 API / 独立重写四条路径之一）。

---

## 2. 底座与 License

### Fork 策略

- **Fork** `NanmiCoder/MediaCrawler`（55k stars，2026-07 仍活跃维护）
- **License**：MediaCrawler 使用 `NON-COMMERCIAL LEARNING LICENSE 1.1`（作者自撰，禁止商用）
- **本项目 License**：跟随 upstream，non-commercial
- **理由**：签名会随平台更新失效，需要长期拉 upstream 修复；Fork 是唯一能持续跟进的形态
- **改造原则**：不动 upstream 原文件（`main.py`、`media_platform/`、`config/base_config.py` 等），所有新代码进 `matcha/` 子目录，独立入口

### 与 MediaCrawler 交互约定

- 保留 `LICENSE` 全文和每个原文件头版权声明
- `matcha/` 目录下新文件用自己的 header
- 修改 upstream 文件的情况**尽量避免**；必要时通过 monkeypatch / 继承 / 组合完成
- 定期 `git fetch upstream && git rebase upstream/main`

---

## 3. 输入与输出

### 输入：达人 CSV

```csv
platform,handle,display_name,note
douyin,matcha_lover_2024,,专精抹茶博主A
douyin,dessert_master,林师傅,日式甜品店主
xhs,matcha_shop_001,和果子小铺,专精和果子
xhs,tokyo_matcha,东京抹茶研究所,
```

- `platform`: `douyin` / `xhs`（v1 只支持这两个）
- `handle`: 抖音短号 / 小红书号（**用户设置的短号，不是 sec_user_id**）
- `display_name`: 昵称，用于小红书搜索结果 disambiguate（抖音选填）
- `note`: 你的备注，不参与抓取

### 输出

1. **SQLite** (`data/matcha.db`)：所有原始数据 + 分数
2. **HTML 报告** (`data/reports/*.html`)：面向业务方，含分数卡片 + 排名
3. **CSV 报告** (`data/reports/*.csv`)：面向 Excel 用户
4. **unresolved.csv**：解析失败的达人，需人工介入

---

## 4. 评分模型 v1（方案 B）

**通用 100 分制，抖音/小红书使用相同框架**：

| 维度 | 权重 | 计算方式 |
|---|---|---|
| **影响力** | 40 | 粉丝分段（5万↑=40 / 1万-5万=30 / 3千-1万=20 / 3千↓=10） |
| **互动率** | 30 | `(avg_liked + comment + collect + share) / follower_count` 分档：>8%=30 / 4-8%=22 / 2-4%=15 / 1-2%=8 / <1%=3 |
| **稳定性** | 15 | 最近 10 条作品互动量 `min/avg` 比：>40%=15 / 20-40%=10 / 10-20%=5 / <10%=2 |
| **相关度** | 15 | 最近 20 条作品命中关键词比例：>70%=15 / 40-70%=10 / 15-40%=6 / <15%=2 |

**评级门槛**：S ≥85 / A 70-85 / B 55-70 / C 40-55 / D <40

**重要说明**：

- 抖音教学版**拿不到 `play_count`**，"互动率"分子只含 赞+评+藏+分享
- **v1 所有阈值都是拍脑袋值**，扫完首批 200 人后回归标定
- 规则代码化 + 阈值配置化（`matcha/scoring/thresholds.yaml`），改数不改代码
- **相关度关键词库** `matcha/keywords/matcha_dessert.yaml` 单独维护，运营可改

---

## 5. 并发与限流策略

### 并发 4 个层次

| 层次 | 策略 | 理由 |
|---|---|---|
| ① 平台间（抖音 vs 小红书） | ✅ 并发 | 不同账号，无风控关联 |
| ② 达人间（同平台同账号） | ❌ 严格顺序 | 单账号 QPS 上升 = 触发风控 |
| ③ 请求间（同达人内多请求） | ❌ 严格顺序 + sleep | MediaCrawler 默认 |
| ④ 抓取 vs 打分（pipeline） | ✅ 并发 | I/O bound vs CPU bound |

### 限流参数（200 人/批安全档）

见 `matcha/config.py::Limits`。

### 200 人时间预算

| 阶段 | 抖音 | 小红书 | 端到端（并行）|
|---|---|---|---|
| 解析（handle → id） | ~10 min | ~17 min | ~17 min |
| 抓取（profile + 20 notes/人）| ~27 min | ~50 min | ~50 min |
| **总计** | **~37 min** | **~67 min** | **~67 min** |

**触发风控自动进冷却**，冷却期间任务持久化到 SQLite，重启不重抓。

---

## 6. 数据模型（SQLite Schema）

见 `matcha/stores/schema.sql`。8 张表：

- `id_resolution` — handle → sec_user_id / user_id+xsec_token 解析缓存
- `creator` — 达人档案（粉丝数、获赞、笔记数等）
- `note` — 作品明细（每达人最近 20 条）
- `score` — 打分结果（分数 + 分档 + 各维度分）
- `scan_task` — 一次扫描任务元数据
- `scan_progress` — 每达人抓取进度（断点续爬关键）
- `rate_limit_event` — 风控事件日志（触发冷却）
- `unresolved_log` — 需人工介入的解析失败记录

---

## 7. 目录结构

```
matcha-kol-scorer-3/
├── (MediaCrawler upstream 文件全部保留不动)
├── main.py                  # MediaCrawler 原 CLI
├── media_platform/          # MediaCrawler 原爬虫
├── config/base_config.py    # MediaCrawler 原配置
│
├── matcha/                  # ← 所有新代码
│   ├── __init__.py
│   ├── config.py            # 运行时配置 + 限流参数
│   ├── cli/                 # Typer CLI 命令
│   ├── crawlers/            # 爬虫适配层（包装 MediaCrawler client）
│   ├── stores/              # SQLite schema + ORM + repositories
│   ├── scoring/             # 评分引擎 + 阈值 YAML
│   ├── pipeline/            # 编排 + 断点续爬 + 限流
│   ├── keywords/            # 相关度关键词库 YAML
│   ├── report/              # HTML/CSV 报告生成
│   └── utils/
│
├── docs/00-mvp-plan.md      # 本文档
├── data/                    # SQLite + 报告输出
├── .env.example
├── README.md
└── pyproject.toml
```

---

## 8. CLI 使用

```bash
matcha init                           # 建 SQLite + 目录
matcha login douyin                   # CDP 扫码
matcha login xhs                      # CDP 扫码
matcha resolve --input creators.csv   # handle → id
matcha scan-and-score --task new      # 抓取 + 打分
matcha status TASK_ID                 # 看进度
matcha report --task TASK_ID          # 出报告
```

---

## 9. 关键改造点（MediaCrawler → 打分需求）

| # | MediaCrawler 现状 | 我们要做的 | 优先级 |
|---|---|---|---|
| 1 | `store_creator` 全平台 `pass` | `matcha/stores/` 自己实现 | P0 |
| 2 | `tools/user_hash.py` 脱敏 | monkeypatch/接管数据流保留原始 uid | P0 |
| 3 | 抖音无 `play_count` | 用（赞+评+藏+分享）合成 | P0 |
| 4 | 无断点续爬 | `pipeline/checkpoint.py` | P0 |
| 5 | search 是搜视频不是搜用户 | `crawlers/douyin_resolver.py` 自己扩 | P0 |
| 6 | 小红书 `xsec_token` 强绑定 | 每次解析同时缓存 token | P0 |
| 7 | 小红书搜索可能多结果 | 用 `display_name` disambiguate | P1 |
| 8 | 无关键词库 | `keywords/matcha_dessert.yaml` | P0 |
| 9 | 无 HTML 报告 | `report/html.py` 简单模板 | P1 |

---

## 10. 开发路线图（4 周 MVP）

| 周 | 目标 | 交付 |
|---|---|---|
| Week 1 | Fork + 环境 + 抖音全链路（20 人 dry run） | `matcha login douyin` + `matcha resolve` + `matcha scan --limit 20` + SQLite 有数据 |
| Week 2 | 抖音评分 + 报告 + 小红书解析器 | `matcha score` + `matcha report` + 抖音 20 人报告能看 |
| Week 3 | 小红书全链路（20 人 dry run） | 小红书跑通端到端 |
| Week 4 | 200 人压测 + 断点续爬 + 冷却机制 + Docs | 200 人一次跑完 + README 完整 |

**里程碑验收**：

- Week 1 末：抖音 20 人成功抓取 + 落 SQLite 且粉丝数字段有值
- Week 2 末：抖音 20 人有 HTML 报告，S/A/B/C/D 分档合理
- Week 3 末：小红书 20 人成功抓取（含 xsec_token 拿到）
- Week 4 末：抖音 100 + 小红书 100 一次跑完不炸

---

## 11. 已确认的技术决策

- Python 3.11+（MediaCrawler 要求）
- DB: SQLite（v1）→ Postgres（v2 商业化时）
- CLI: Typer
- ORM: SQLAlchemy 2.0 async
- HTTP: 延续 MediaCrawler 的 httpx + Playwright CDP
- 报告: Jinja2 + 内嵌 CSS 单文件 HTML
- 打包: pyproject.toml (PEP 621)
- Node ≥16（抖音 a_bogus 签名需要）

---

## 12. 待决策事项

- [ ] IP 代理是否接入（MVP 单账号可不接）
- [ ] 冷启动打分是否需要基线数据集校准阈值
- [ ] 报告要不要含"建议报价"（CPM × avg_views）
- [ ] 多账号轮换（v2 才做）
- [ ] MCP server 封装（可选）

---

## Changelog

- **2026-07-04 v0.1**：初版落地
