"""数字格式化工具：Star 数缩写等。"""


def format_stars(value: int | None) -> str:
    """把 Star 数格式化为 12.3k / 1.2M 形式，小于 1000 时原样返回。"""
    if value is None:
        return "0"
    if value < 1000:
        return str(value)
    if value < 1_000_000:
        return f"{value / 1000:.1f}k".replace(".0k", "k")
    return f"{value / 1_000_000:.1f}M".replace(".0M", "M")


def safe_rate(numerator: int, denominator: int) -> float:
    """安全计算比率，分母为 0 时返回 0.0。"""
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)
