"""Matcha KOL Scorer CLI entry.

    matcha init | login | resolve | scan | score | scan-and-score | status | report
"""

from __future__ import annotations

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
    typer.echo(f"[TODO Week1] 登录 {platform}（CDP + 扫码）")


@app.command()
def resolve(
    input: str = typer.Option(..., "--input", "-i", help="CSV 文件路径"),
    task: str = typer.Option("auto", "--task", "-t", help="任务 ID 或 auto"),
) -> None:
    """解析 handle → 内部 ID（结果落 SQLite 缓存）."""
    typer.echo(f"[TODO Week1] 解析 {input}")


@app.command()
def scan(
    task: str = typer.Option("new", "--task", "-t", help="new / TASK_ID"),
    resume: str | None = typer.Option(None, "--resume", "-r"),
    limit: int | None = typer.Option(None, "--limit", "-l", help="只处理前 N 个"),
) -> None:
    """抓取达人档案 + 最近 N 条作品."""
    typer.echo(f"[TODO Week1] scan task={task} limit={limit}")


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
    typer.echo(f"[TODO Week1] status {task_id}")


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
