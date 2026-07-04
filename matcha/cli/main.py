"""Matcha KOL Scorer CLI entry.

    matcha init | login | resolve | scan | score | scan-and-score | status | report
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="matcha",
    help="Matcha KOL Scorer — 抖音/小红书达人批量评分工具",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def init() -> None:
    """初始化数据库与目录."""
    from matcha.config import DB_PATH, ensure_dirs
    from matcha.stores.db import init_db

    ensure_dirs()
    init_db()
    typer.echo(f"✓ SQLite 已初始化: {DB_PATH}")
    typer.echo("✓ 目录已创建: data/, data/raw/, data/reports/")
    typer.echo("→ 下一步: matcha login douyin")


@app.command()
def login(platform: str = typer.Argument(..., help="douyin | xhs")) -> None:
    """扫码登录并保持登录态（CDP 模式）."""
    typer.echo(f"[TODO Week1 Day4] 登录 {platform}（CDP + 扫码）")


@app.command()
def resolve(
    input: str = typer.Option(..., "--input", "-i", help="CSV 文件路径"),
    force: bool = typer.Option(
        False, "--force", "-f", help="忽略缓存, 全部重新解析"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="只解析不落库, 打印结果预览"
    ),
) -> None:
    """解析 handle → 内部 ID (结果落 SQLite 缓存).

    对每个输入 handle:
      1. 若已在 id_resolution 表中 status=resolved 且未过期 → 跳过 (除非 --force)
      2. 否则调用平台 resolver 走 search API
      3. 结果 upsert 到 id_resolution 表
    """
    from matcha.utils.csv_io import group_by_platform, parse_creators_csv

    csv_path = Path(input)
    try:
        creators = parse_creators_csv(csv_path)
    except FileNotFoundError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(code=1) from e
    except Exception as e:
        typer.echo(f"✗ CSV 解析失败: {e}", err=True)
        raise typer.Exit(code=1) from e

    grouped = group_by_platform(creators)
    typer.echo(f"读取 {len(creators)} 行: douyin={len(grouped['douyin'])}, xhs={len(grouped['xhs'])}")

    if dry_run:
        typer.echo("[dry-run] 不落库, 不调用远程接口")
        for c in creators[:5]:
            typer.echo(f"  · {c.platform} / {c.handle} / {c.display_name or ''}")
        if len(creators) > 5:
            typer.echo(f"  ... 还有 {len(creators) - 5} 个")
        return

    # 真正的解析流程需要 MediaCrawler client (playwright + 登录态)
    # Week 1 Day 4 前先只支持读缓存:
    from matcha.stores.resolution_repo import ResolutionRepo

    repo = ResolutionRepo()
    hits = 0
    misses = 0
    for c in creators:
        cached = repo.get(c.platform, c.handle)
        if cached and cached.status == "resolved" and not force:
            hits += 1
        else:
            misses += 1

    typer.echo(f"缓存命中: {hits}, 待解析: {misses}")
    if misses:
        typer.echo(
            "→ 未缓存的 handle 需要抖音登录态才能解析. "
            "请先运行: matcha login douyin",
            err=True,
        )
        typer.echo("  (Week 1 Day 4 后完整支持)")
    typer.echo(f"✓ 解析完成. 详细状态: matcha status (查看)")


@app.command()
def scan(
    task: str = typer.Option("new", "--task", "-t", help="new / TASK_ID"),
    resume: str | None = typer.Option(None, "--resume", "-r"),
    limit: int | None = typer.Option(None, "--limit", "-l"),
) -> None:
    """抓取达人档案 + 最近 N 条作品."""
    typer.echo(f"[TODO Week1 Day5] scan task={task} limit={limit}")


@app.command()
def score(task: str = typer.Option(..., "--task", "-t")) -> None:
    """对已抓取达人打分."""
    typer.echo(f"[TODO Week2] score task={task}")


@app.command(name="scan-and-score")
def scan_and_score(
    task: str = typer.Option("new", "--task", "-t"),
    limit: int | None = typer.Option(None, "--limit", "-l"),
) -> None:
    """抓取 + 打分一步到位."""
    typer.echo(f"[TODO Week2] scan-and-score task={task} limit={limit}")


@app.command()
def status(task_id: str = typer.Argument(...)) -> None:
    """查看任务进度."""
    typer.echo(f"[TODO Week1 Day5] status {task_id}")


@app.command()
def report(
    task: str = typer.Option(..., "--task", "-t"),
    top: int = typer.Option(30, "--top"),
    format: str = typer.Option("html", "--format", "-f", help="html | csv"),
    out: str | None = typer.Option(None, "--out", "-o"),
) -> None:
    """生成 HTML/CSV 报告."""
    typer.echo(f"[TODO Week2] report task={task} top={top} format={format}")


if __name__ == "__main__":
    app()
