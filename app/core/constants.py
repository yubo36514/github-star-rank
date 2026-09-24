"""全局常量定义。"""

# 列表接口允许的排序字段 -> ORM 字段映射
SORTABLE_FIELDS = {
    "stars_7d": "stars_7d",
    "total_stars": "total_stars",
    "stars_7d_rate": "stars_7d_rate",
    "created_at": "repo_created_at",
    "first_seen_at": "first_seen_at",
    "forks_count": "forks_count",
    "stars_1d": "stars_1d",
}
DEFAULT_SORT_BY = "stars_7d"

# 分页参数的合法取值
PAGE_SIZE_CHOICES = (10, 20, 50, 100)
DEFAULT_PAGE_SIZE = 20

# 无语言时的归一化取值
UNKNOWN_LANGUAGE = "Unknown"

# Github 官方语言色值（用于前端圆点），未在表中的语言回退到 DEFAULT_LANGUAGE_COLOR
LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "C": "#555555",
    "C#": "#178600",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Shell": "#89e051",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Vue": "#41b883",
    "Jupyter Notebook": "#DA5B0B",
    "Dart": "#00B4AB",
    "Scala": "#c22d40",
    "Lua": "#000080",
    "Elixir": "#6e4a7e",
    "Zig": "#ec915c",
    "Unknown": "#8b949e",
}
DEFAULT_LANGUAGE_COLOR = "#8b949e"


def language_color(language: str | None) -> str:
    """获取语言对应的展示色，未收录则返回默认灰色。"""
    if not language:
        return DEFAULT_LANGUAGE_COLOR
    return LANGUAGE_COLORS.get(language, DEFAULT_LANGUAGE_COLOR)
