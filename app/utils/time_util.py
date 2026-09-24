"""时间处理工具。"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


def today_str() -> str:
    """当前日期字符串 YYYY-MM-DD（UTC）。"""
    return datetime.now(UTC).date().isoformat()


def days_ago_str(days: int) -> str:
    """N 天前的日期字符串 YYYY-MM-DD。"""
    return (datetime.now(UTC).date() - timedelta(days=days)).isoformat()


def date_str(d: date | datetime) -> str:
    return d.strftime("%Y-%m-%d")


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def iso_or_empty(dt: datetime | None) -> str:
    """把 datetime 转成接口友好的字符串。"""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def parse_github_time(value: str | None) -> str | None:
    """Github 返回的 ISO8601 时间（如 2024-01-01T10:00:00Z）原样返回即可。"""
    return value or None
