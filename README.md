# Github 7 日新增 Star 项目榜单系统

定时抓取 Github 官方 API，按近 7 日新增 Star 数生成热门开源项目榜单。

> 说明：Github 没有官方 Trending API。本项目通过「每日快照 + 差值计算」得到真实的 7 日增量，并通过数据库缓存与请求限流最大程度降低对 Github API 的压力。

## 技术栈

- **后端**：Python 3.12 + FastAPI + SQLAlchemy 2.0 + SQLite + APScheduler
- **依赖管理**：[uv](https://docs.astral.sh/uv/)
- **前端**：原生 HTML + TailwindCSS（Play CDN，已 vendor 到本地）+ [particles.js](https://vincentgarreau.com/particles.js/)
- **部署**：Docker + docker-compose

## 核心功能

- 每日定时抓取 Github Search API，构建候选仓库池并写入今日快照
- 计算每个仓库近 1 日 / 7 日新增 Star 与增长率
- 7 日新增 Star 榜单（支持分页、编程语言多选、关键词搜索、排序）
- 收藏功能：无需登录，浏览器 `localStorage` 生成 `X-Client-Id`，服务端隔离
- 项目详情抽屉 + 近 8 日 Star 趋势折线图
- 粒子特效背景，支持 `prefers-reduced-motion` 降级
- 缓存机制：Github API 响应进入 SQLite 缓存，重复请求不消耗配额
- Github API 配额监控与限流保护

## 目录结构

```
.
├── app/                  # 后端 FastAPI 应用
│   ├── api/              # RESTful 接口
│   ├── core/             # 常量、异常、安全工具
│   ├── db/               # 数据库引擎与初始化
│   ├── models/           # SQLAlchemy ORM 模型
│   ├── repositories/     # 数据访问层
│   ├── schemas/          # Pydantic 模型
│   ├── services/         # 业务逻辑 + Github 采集
│   ├── tasks/            # APScheduler 定时任务
│   └── utils/            # 通用工具
├── web/                  # 前端静态页面
│   ├── index.html
│   ├── assets/css/
│   └── assets/js/
├── pyproject.toml        # uv 项目配置与依赖
├── uv.lock               # 锁定文件
├── Dockerfile
├── docker-compose.yml
└── .env.example          # 环境变量示例
```

## 环境变量

参考 `.env.example`，主要变量如下：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DATABASE_URL` | SQLite 连接串 | `sqlite+aiosqlite:///./data/app.db` |
| `GITHUB_TOKEN` | Github Personal Access Token（强烈建议配置） | 空 |
| `GITHUB_REQUEST_INTERVAL` | 请求间隔（秒） | `0.7` |
| `GITHUB_CACHE_TTL` | Github API 响应缓存时间（秒） | `21600`（6 小时） |
| `FETCH_CRON_HOUR` | 每日抓取 UTC 小时 | `0`（北京时间 08:00） |
| `DELTA_CRON_HOUR` | 每日增量计算 UTC 小时 | `1`（北京时间 09:00） |
| `ADMIN_TOKEN` | 管理接口鉴权 | `change-me-please` |
| `CORS_ORIGINS` | 允许的前端来源 | `*` |
| `DEMO_SEED_ON_EMPTY` | 数据库为空时自动写入演示数据 | `true` |

## 本地启动方式（uv）

### 1. 安装 uv

```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 克隆并进入项目

```bash
cd github-star-ranking
cp .env.example .env
```

编辑 `.env`，至少修改：

```bash
# 强烈建议填写，否则只有 60 次/小时，项目会主动降速
GITHUB_TOKEN=ghp_xxx

# 必须修改
ADMIN_TOKEN=your-strong-admin-token
```

### 3. 安装依赖并启动

```bash
# 安装依赖（会读取 pyproject.toml 与 uv.lock）
uv sync

# 开发模式启动（热重载）
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式启动
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### 4. 访问

- 前端页面：http://localhost:8000/
- 接口文档：http://localhost:8000/api/docs
- 健康检查：http://localhost:8000/api/v1/health

首次启动时如果数据库为空，会自动写入 120 条演示数据（带 8 天历史快照），直接刷新页面即可看到榜单。

### 常用命令

```bash
# 手动触发一次 Github 数据抓取（需要 ADMIN_TOKEN）
curl -X POST http://localhost:8000/api/v1/admin/refresh \
     -H "X-Admin-Token: <ADMIN_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"force": true}'

# 代码检查
uv run ruff check app

# 运行测试
uv run pytest
```

## Docker 部署（推荐）

### 一键启动

```bash
cp .env.example .env
# 编辑 .env，填入 GITHUB_TOKEN 与 ADMIN_TOKEN

docker compose up -d --build
```

等待约 10 秒后访问 http://localhost:8000/。

### 常用运维

```bash
# 查看日志
docker compose logs -f gh-star-ranking

# 手动触发数据刷新
curl -X POST http://localhost:8000/api/v1/admin/refresh \
     -H "X-Admin-Token: <ADMIN_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"force": true}'

# 停止
docker compose down

# 更新（拉取新版代码后重建）
docker compose down
docker compose up -d --build
```

### 数据持久化

SQLite 数据库文件保存在 Docker 命名卷 `gh-star-data` 中：

```bash
# 查看卷位置
docker volume inspect gh-star-data

# 备份容器内数据库
docker exec gh-star-ranking sqlite3 /app/data/app.db ".backup /app/data/backup.db"
```

### 不使用 docker-compose 直接运行 Docker

```bash
docker build -t github-star-ranking:0.1.0 .
docker run -d \
  -p 8000:8000 \
  -v gh-star-data:/app/data \
  -v gh-star-logs:/app/logs \
  -e GITHUB_TOKEN=ghp_xxx \
  -e ADMIN_TOKEN=your-strong-admin-token \
  --name github-star-ranking \
  github-star-ranking:0.1.0
```

## 关键 API

| 接口 | 说明 |
| --- | --- |
| `GET /api/v1/repos` | 榜单列表（分页、语言筛选、关键词、排序） |
| `GET /api/v1/repos/{repo_id}` | 项目详情 + 7 日趋势 |
| `GET /api/v1/languages` | 编程语言列表 |
| `POST /api/v1/favorites` | 收藏 |
| `DELETE /api/v1/favorites/{repo_id}` | 取消收藏 |
| `GET /api/v1/favorites/ids` | 收藏 ID 集合 |
| `GET /api/v1/meta/stats` | 全局统计 |
| `POST /api/v1/admin/refresh` | 手动触发数据抓取 |

## 生产建议

1. **配置 Github Token**：未认证时 Github 每小时仅 60 次请求，认证后 5000 次。未认证状态下应用会自动降低请求频率并可能触发「今日已抓取」跳过。
2. **修改默认 ADMIN_TOKEN**：否则任何人都能触发手动刷新。
3. **HTTPS**：在容器前加 Nginx / Traefik / Caddy 做 HTTPS 与静态资源压缩。
4. **备份**：建议每天备份一次 `data/app.db`。
5. **关闭演示数据**：数据库已有真实数据后，设置 `DEMO_SEED_ON_EMPTY=false`。

## 许可

MIT
