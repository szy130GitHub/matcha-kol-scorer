# Matcha KOL Scorer

> 抖音 / 小红书达人批量评分工具（面向泛日式甜品 / 抹茶方向）
>
> **状态**：MVP 骨架 · v0.1 · 2026-07-04

## 是什么

给品牌方（泛日式甜品/抹茶）批量评估达人的开源命令行工具：

1. 你给一份达人 CSV（抖音短号 / 小红书号）
2. 工具自动解析 ID、抓取主页 + 最近 20 条作品
3. 按「影响力 40 + 互动率 30 + 稳定性 15 + 相关度 15」四维打分
4. 输出 S/A/B/C/D 分档报告（HTML + CSV）

MVP 一次评估 200 达人，端到端约 1 小时。

## 关系与 License

本项目 **Fork 自 [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)**：

- **License**：跟随 upstream 使用 `NON-COMMERCIAL LEARNING LICENSE 1.1`
- **仅供学习和研究用途**，禁止商业用途，禁止大规模爬取
- 商用请走 [MediaCrawlerPro](https://github.com/MediaCrawlerPro) 授权或第三方数据 API

在 upstream 之上，本项目新增：

- `matcha/` — 所有自研代码（爬虫适配层、评分引擎、报告生成、CLI）
- `docs/` — 需求与设计文档
- `data/` — 运行时数据（SQLite + 报告）

**不修改 upstream 原文件**，通过 monkeypatch / 继承 / 组合复用 MediaCrawler 的 client 与 login。

## 输入格式

```csv
platform,handle,display_name,note
douyin,matcha_lover_2024,,专精抹茶博主
xhs,tokyo_matcha,东京抹茶研究所,专精抹茶
```

- `platform`: `douyin` / `xhs`
- `handle`: 抖音短号 / 小红书号（**用户设置的短号，不是 sec_user_id**）
- `display_name`: 昵称，小红书解析时用于去重
- `note`: 你的备注

## 评分模型 v1

| 维度 | 权重 | 说明 |
|---|---|---|
| 影响力 | 40 | 粉丝分段 |
| 互动率 | 30 | (avg_liked + comment + collect + share) / follower |
| 稳定性 | 15 | 最近 10 条作品互动量 min/avg |
| 相关度 | 15 | 最近 20 条命中「抹茶/日式甜品」关键词比例 |

评级：S ≥85 / A 70-85 / B 55-70 / C 40-55 / D <40。阈值全部在 `matcha/scoring/thresholds.yaml`。

## 并发与限流

- **平台间并行**（抖音 + 小红书同时跑）
- **平台内顺序**（单账号 QPS 保护）
- **抓打 pipeline**（抓一个立刻打分）
- 触发风控自动进冷却，写 SQLite 断点续爬

## 快速开始（骨架就绪，实现进行中）

```bash
git clone <YOUR_FORK_URL> && cd matcha-kol-scorer
uv pip install -r requirements.txt
uv pip install -e .
playwright install chromium
cp .env.example .env

matcha init
matcha login douyin
matcha login xhs

matcha resolve --input creators.csv
matcha scan-and-score --task new
matcha report --task <TASK_ID> --top 30 --format html
```

## 目录结构

```
matcha/                     # 自研代码
├── config.py               # 运行时配置 + 限流参数
├── cli/                    # Typer CLI 命令
├── crawlers/               # 爬虫适配层（包装 MediaCrawler client）
├── stores/                 # SQLite schema + ORM + repositories
├── scoring/                # 评分引擎 + 阈值 YAML
├── pipeline/               # 编排 + 断点续爬 + 限流
├── keywords/               # 相关度关键词库 YAML
└── report/                 # HTML/CSV 报告生成

docs/00-mvp-plan.md         # 完整设计（唯一真相源）
data/matcha.db              # SQLite
data/reports/               # 生成的 HTML/CSV 报告
```

## 开发路线图（4 周 MVP）

| 周 | 目标 |
|---|---|
| Week 1 | 抖音全链路（20 人 dry run） |
| Week 2 | 评分 + HTML 报告 + 小红书解析器 |
| Week 3 | 小红书全链路（20 人 dry run） |
| Week 4 | 200 人压测 + 断点续爬 + 冷却机制 |

详见 [`docs/00-mvp-plan.md`](docs/00-mvp-plan.md)。

## Credits

- Fork base：[NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)
- 签名依赖：`xhshow`（小红书）、`pyexecjs + webmssdk.js`（抖音 a_bogus）

## License

NON-COMMERCIAL LEARNING LICENSE 1.1（同 upstream）。
