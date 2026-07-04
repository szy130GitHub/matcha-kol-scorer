"""Matcha KOL Scorer — 配置层.

覆盖 MediaCrawler 的 ``config/base_config.py``，从 ``.env`` 读取运行时参数。
所有限流参数、阈值、路径都在这里集中管理，方便调整不改代码。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "matcha.db"
REPORTS_DIR = DATA_DIR / "reports"
RAW_DIR = DATA_DIR / "raw"

# 关键词库
KEYWORDS_DIR = PROJECT_ROOT / "matcha" / "keywords"
KEYWORDS_FILE = KEYWORDS_DIR / "matcha_dessert.yaml"

# 评分阈值
SCORING_THRESHOLDS = PROJECT_ROOT / "matcha" / "scoring" / "thresholds.yaml"
THRESHOLDS_VERSION = "v1.0"


@dataclass(frozen=True)
class Limits:
    """限流参数. 修改前务必阅读 docs/00-mvp-plan.md."""

    # 抖音
    DY_SLEEP_MIN: float = 2.0
    DY_SLEEP_MAX: float = 3.5
    DY_LONG_REST_EVERY: int = 20
    DY_LONG_REST_SEC: int = 30
    DY_DAILY_MAX_CREATOR: int = 300

    # 小红书（更保守）
    XHS_SLEEP_MIN: float = 4.0
    XHS_SLEEP_MAX: float = 6.5
    XHS_LONG_REST_EVERY: int = 15
    XHS_LONG_REST_SEC: int = 60
    XHS_DAILY_MAX_CREATOR: int = 200

    # 风控冷却（秒）
    COOLDOWN_ON_471: int = 30 * 60
    COOLDOWN_ON_300012: int = 60 * 60
    COOLDOWN_ON_AI_DETECT: int = 24 * 3600

    # 重试
    RETRY_MAX: int = 3
    RETRY_BACKOFF: tuple[int, ...] = (2, 8, 30)

    # 每达人最多抓多少条笔记
    NOTES_PER_CREATOR: int = 20


LIMITS = Limits()


def _env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes", "on"}


HEADLESS = _env_bool("MATCHA_HEADLESS", default=False)
USE_CDP = _env_bool("MATCHA_USE_CDP", default=True)
CDP_PORT = int(os.environ.get("MATCHA_CDP_PORT", "9222"))
ENABLE_IP_PROXY = _env_bool("MATCHA_IP_PROXY", default=False)
IP_PROXY_PROVIDER = os.environ.get("MATCHA_IP_PROXY_PROVIDER", "static")
LOG_LEVEL = os.environ.get("MATCHA_LOG_LEVEL", "INFO")


def apply_to_mediacrawler() -> None:
    """将本模块参数注入 MediaCrawler 的 config.base_config."""
    try:
        from config import base_config as bc  # type: ignore
    except ImportError:
        return
    bc.MAX_CONCURRENCY_NUM = 1
    bc.CRAWLER_MAX_SLEEP_SEC = LIMITS.DY_SLEEP_MIN
    bc.CRAWLER_MAX_NOTES_COUNT = LIMITS.NOTES_PER_CREATOR
    bc.HEADLESS = HEADLESS
    bc.ENABLE_CDP_MODE = USE_CDP
    bc.CDP_DEBUG_PORT = CDP_PORT
    bc.ENABLE_IP_PROXY = ENABLE_IP_PROXY
    bc.IP_PROXY_PROVIDER_NAME = IP_PROXY_PROVIDER


def ensure_dirs() -> None:
    for d in (DATA_DIR, REPORTS_DIR, RAW_DIR):
        d.mkdir(parents=True, exist_ok=True)
