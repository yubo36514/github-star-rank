# 多阶段构建：
# Stage 1 用 uv 镜像安装依赖并生成 .venv
# Stage 2 用轻量 python-slim 镜像运行应用

# ---------- Stage 1: builder ----------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=0

WORKDIR /app

# 复制 lock 与项目配置，最大化 Docker 构建缓存
COPY pyproject.toml uv.lock ./

# 仅安装依赖（不安装项目自身），生成可复用 .venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    PATH="/app/.venv/bin:$PATH" \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

WORKDIR /app

# 安装容器内常用工具
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 创建非 root 运行用户
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

# 从 builder 复制已准备好的虚拟环境
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# 复制应用代码与前端静态资源
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser web ./web
COPY --chown=appuser:appuser pyproject.toml README.md ./

# 数据与日志目录（通过卷挂载持久化）
RUN mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# 容器健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

# 使用单 worker（SQLite 场景限制为 1，避免并发写锁）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
