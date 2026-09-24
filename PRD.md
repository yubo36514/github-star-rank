# PRD：Github 7 日新增 Star 项目榜单系统

| 项目 | 内容 |
| --- | --- |
| 文档名称 | Github 7 日新增 Star 项目榜单系统 PRD |
| 文档版本 | v1.0 |
| 最后更新 | 2026-09-23 |
| 产品形态 | 纯 Web 网页应用（不含 APP、不含 PWA） |
| 后端技术栈 | Python 3.12 + FastAPI + SQLAlchemy 2.0 + SQLite + uv |
| 前端技术栈 | 原生 HTML/CSS/JS（ES Module）+ Canvas 粒子特效（无重框架依赖） |

---

## 1. 项目简介

### 1.1 背景

Github 上每天都有大量新项目诞生，也有老项目因某个版本发布、某篇文章推荐而突然爆火。Github 官方仅提供「Trending」页面，且**不提供官方 Trending API**，也不提供「近 7 日新增 Star 数」这一维度，开发者难以高效发现「近期正在快速增长」的优质项目。

本项目通过**定时调用 Github 官方 Search API / Repository API**，对一批候选仓库做**每日快照**，从而计算出每个仓库**近 7 日的 Star 净增量**，并以榜单形式在网页中呈现，帮助用户快速发现近期热门项目。

### 1.2 产品定位

一个轻量、可自部署、开箱即用的「Github 项目 7 日 Star 增长榜」Web 应用，面向开发者、技术投资人、技术媒体编辑等希望追踪开源热度趋势的人群。

### 1.3 目标用户

| 用户类型 | 核心诉求 |
| --- | --- |
| 开发者 | 发现值得学习/使用的新兴开源项目 |
| 技术leader / 架构师 | 评估某个技术方向的社区热度与选型趋势 |
| 技术投资人 / 分析师 | 追踪开源赛道增长数据，辅助判断 |
| 技术媒体 / 内容创作者 | 快速获取选题素材与热点项目 |

### 1.4 核心目标与成功指标

- 数据每日自动更新一次，7 日 Star 增量计算准确率 100%（基于快照差值）。
- 榜单支持 TOP 500 仓库的稳定展示与查询。
- 首屏加载（含粒子特效）在普通网络下 ≤ 2.5s，接口 P95 ≤ 300ms。
- 单个 Github Token 下每日 API 调用量控制在配额内（未认证 60 次/小时，认证 5000 次/小时）。

### 1.5 名词解释

| 名词 | 说明 |
| --- | --- |
| 7 日新增 Star（`stars_7d`） | 当前快照 `stargazers_count` 与 7 天前同一仓库快照的差值 |
| 快照（Snapshot） | 定时任务在某一时刻拉取到的仓库 Star 数等指标的存档记录 |
| 候选池（Candidate Pool） | 通过 Github Search API 拉取、待纳入跟踪的仓库集合 |
| 收藏（Favorite） | 用户在本地/服务端标记关注的项目，服务端按客户端标识隔离 |

### 1.6 不做的事（Out of Scope）

- 不做移动端 APP、不做 PWA、不做离线安装。
- 不做用户登录注册体系（收藏功能采用轻量客户端标识，见 4.5）。
- 不做 Github OAuth 授权登录、不做评论/社交互动。
- 不做多租户与付费体系。

---

## 2. 功能清单

### 2.1 功能总览

| 编号 | 模块 | 功能点 | 优先级 |
| --- | --- | --- | --- |
| F-B01 | 后端 | Github 数据定时拉取与快照入库 | P0 |
| F-B02 | 后端 | 7 日 Star 增量计算与榜单生成 | P0 |
| F-B03 | 后端 | 榜单查询接口（分页 / 语言筛选 / 排序 / 关键词） | P0 |
| F-B04 | 后端 | 项目详情接口（含 7 日 Star 趋势曲线数据） | P1 |
| F-B05 | 后端 | 收藏接口（新增 / 取消 / 列表 / 批量查询） | P0 |
| F-B06 | 后端 | Github API 配额管理与限流保护 | P1 |
| F-B07 | 后端 | 手动触发数据刷新（管理接口，Token 保护） | P1 |
| F-B08 | 后端 | 健康检查与数据统计接口 | P2 |
| F-F01 | 前端 | 粒子特效背景（Canvas，性能自适应 + 降级） | P0 |
| F-F02 | 前端 | Top 3 卡片高亮展示 + 项目卡片列表 | P0 |
| F-F03 | 前端 | 分页浏览 | P0 |
| F-F04 | 前端 | 编程语言筛选 | P0 |
| F-F05 | 前端 | 关键词搜索 | P1 |
| F-F06 | 前端 | 排序切换（7 日增量 / 总 Star / 新增时间） | P1 |
| F-F07 | 前端 | 收藏 / 取消收藏（含「只看收藏」视图） | P0 |
| F-F08 | 前端 | 项目详情抽屉（趋势迷你图 + 外链跳转） | P1 |
| F-F09 | 前端 | 数据更新时间展示 + 手动刷新提示 | P1 |
| F-F10 | 前端 | 响应式布局（桌面 / 平板 / 手机浏览器） | P1 |
| F-F11 | 前端 | 骨架屏 / 加载态 / 空态 / 错误态 | P1 |

### 2.2 后端接口清单

统一前缀：`/api/v1`。所有响应统一封装为 `{ code, message, data, timestamp }`（`code = 0` 表示成功）。

| 编号 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| B01 | GET | `/api/v1/repos` | 榜单列表（分页、筛选、排序、搜索） |
| B02 | GET | `/api/v1/repos/{repo_id}` | 项目详情（含趋势序列） |
| B03 | GET | `/api/v1/languages` | 可选编程语言列表（带项目计数） |
| B04 | GET | `/api/v1/favorites` | 收藏列表 |
| B05 | POST | `/api/v1/favorites` | 新增收藏 |
| B06 | DELETE | `/api/v1/favorites/{repo_id}` | 取消收藏 |
| B07 | GET | `/api/v1/favorites/ids` | 收藏 ID 集合（批量点亮卡片星标） |
| B08 | GET | `/api/v1/meta/stats` | 全局统计（收录数、更新时间、API 配额剩余） |
| B09 | GET | `/api/v1/meta/languages-trend` | 语言维度热度聚合（可选） |
| B10 | POST | `/api/v1/admin/refresh` | 手动触发数据拉取（需 Header `X-Admin-Token`） |
| B11 | GET | `/api/v1/health` | 健康检查 |

#### B01 `GET /api/v1/repos`

请求参数：

| 参数 | 类型 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | int | 否 | 1 | 页码，从 1 开始 |
| `page_size` | int | 否 | 20 | 每页条数，取值 10/20/50 |
| `language` | string | 否 | 空 | 编程语言，支持多值逗号分隔，如 `Python,Go` |
| `keyword` | string | 否 | 空 | 仓库名 / 描述模糊匹配 |
| `sort_by` | string | 否 | `stars_7d` | 枚举：`stars_7d` / `total_stars` / `created_at` / `stars_7d_rate` |
| `order` | string | 否 | `desc` | `desc` / `asc` |
| `only_favorites` | bool | 否 | false | 仅返回当前客户端收藏的项目 |
| `client_id` | string | 否 | 空 | 来自 Header `X-Client-Id`，用于收藏过滤 |

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "timestamp": 1758604800,
  "data": {
    "total": 486,
    "page": 1,
    "page_size": 20,
    "updated_at": "2026-09-23 08:00:12",
    "items": [
      {
        "id": 1024,
        "repo_id": 987654321,
        "full_name": "owner/repo",
        "owner": "owner",
        "name": "repo",
        "description": "A blazing fast ...",
        "language": "Python",
        "html_url": "https://github.com/owner/repo",
        "homepage": "https://example.com",
        "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
        "topics": ["ai", "llm"],
        "total_stars": 128000,
        "forks_count": 9000,
        "open_issues_count": 320,
        "stars_7d": 3421,
        "stars_7d_rate": 0.0275,
        "stars_1d": 512,
        "created_at": "2024-03-01T10:00:00Z",
        "pushed_at": "2026-09-22T10:00:00Z",
        "is_favorite": false,
        "rank": 1
      }
    ]
  }
}
```

#### B02 `GET /api/v1/repos/{repo_id}`

返回项目详情及 `trend` 字段（近 7 日每日 Star 数与增量）：

```json
{
  "code": 0,
  "data": {
    "repo": { "...同上..." },
    "trend": [
      { "date": "2026-09-16", "total_stars": 124800, "delta": 480 },
      { "date": "2026-09-23", "total_stars": 128221, "delta": 512 }
    ]
  }
}
```

#### B03 `GET /api/v1/languages`

```json
{ "code": 0, "data": [{ "name": "Python", "count": 128 }, { "name": "Go", "count": 96 }] }
```

#### B05 `POST /api/v1/favorites`

请求体：`{ "repo_id": 987654321 }`，Header 需携带 `X-Client-Id`。
响应：`{ "code": 0, "data": { "repo_id": 987654321, "is_favorite": true } }`，重复收藏幂等返回成功。

#### B10 `POST /api/v1/admin/refresh`

请求体：`{ "force": false }`（`force=true` 忽略「今日已更新」判断）。
Header：`X-Admin-Token: <ADMIN_TOKEN>`；缺失或错误返回 `403`。
响应：`{ "code": 0, "data": { "task_id": "...", "fetched": 486, "duration_ms": 12345 } }`

#### 统一错误码

| code | HTTP | 含义 |
| --- | --- | --- |
| 0 | 200 | 成功 |
| 40001 | 400 | 参数校验失败 |
| 40401 | 404 | 资源不存在 |
| 40301 | 403 | 无权限（Admin Token 错误） |
| 42901 | 429 | Github API 配额耗尽，请稍后重试 |
| 50001 | 500 | 服务内部错误 |

### 2.3 定时任务设计

| 任务 | 调度 | 说明 |
| --- | --- | --- |
| `fetch_daily_snapshot` | 每日 08:00（Asia/Shanghai，Cron `0 0 * * *` UTC） | 拉取候选池仓库最新数据并写入快照表 |
| `discover_new_repos` | 每日 07:30 | 通过 Search API 扩充候选池（近 30 日创建 / 高 Star 项目） |
| `compute_stars_delta` | 每日 08:30（依赖快照任务） | 计算 `stars_1d` / `stars_7d` / `stars_7d_rate` 并更新榜单表 |
| `cleanup_old_snapshots` | 每周一 03:00 | 清理超过 90 天的快照记录，控制数据库体积 |

调度实现：`APScheduler`（`AsyncIOScheduler`）+ 应用内单例锁，避免多副本重复执行（SQLite 单副本部署，同时用 `_scheduler_lock` 表做兜底）。

### 2.4 Github API 使用策略

数据来源（全部为 Github 官方 API）：

1. **发现候选**：`GET https://api.github.com/search/repositories`
   - 条件示例：`q=created:>{30天前} sort:stars order:desc`、`q=stars:>500 pushed:>{7天前}`
   - 分页取 `per_page=100`，最多 5 页（即 500 个候选），避免配额浪费。
2. **详情与快照**：`GET https://api.github.com/repos/{owner}/{repo}`（获取 `stargazers_count` 等）

策略要点：

- 使用 `GITHUB_TOKEN`（可选，未配置则匿名 60 次/小时，自动降低抓取规模）。
- 串行请求 + 请求间隔 `0.7s`（可配置） + 指数退避重试（最多 3 次）。
- 读取响应头 `X-RateLimit-Remaining`，低于阈值（默认 50）时中断本轮任务并记录告警日志，保留已抓取数据。
- 处理 `403 secondary rate limit` 与 `409 Conflict`，遇到时暂停并写入日志。

### 2.5 前端页面功能

| 编号 | 功能 | 描述 |
| --- | --- | --- |
| F-F01 | 粒子特效背景 | 全屏 `<canvas>`，粒子 + 连线；支持鼠标交互；`prefers-reduced-motion` 或低端设备下自动降级为静态渐变背景；页面不可见时暂停渲染 |
| F-F02 | 榜单卡片 | Top 3 使用大卡 + 排名徽章（金/银/铜），其余为列表卡片；卡片展示排名、仓库名、描述、语言色点、总 Star、7 日新增、日均增速 |
| F-F03 | 分页 | 底部分页器（上一页/下一页 + 页码），支持 `page_size` 切换，翻页后滚动到列表顶部并保留筛选条件 |
| F-F04 | 语言筛选 | 顶部语言下拉/标签组，数据来源 `/api/v1/languages`，支持多选（逗号拼接），选中态高亮 |
| F-F05 | 关键词搜索 | 搜索框输入回车触发，300ms 防抖，支持仓库名与描述匹配 |
| F-F06 | 排序切换 | Tab 切换：7 日新增（默认）/ 总 Star / 增速 / 最新收录 |
| F-F07 | 收藏 | 卡片右上角星标按钮，点击乐观更新 + 调用接口；顶部「只看收藏」开关；`X-Client-Id` 存于 `localStorage`（键 `gh_rank_client_id`） |
| F-F08 | 详情抽屉 | 点击卡片打开右侧抽屉，展示 README 摘要、Topics、7 日趋势迷你折线图、「在 Github 打开」按钮 |
| F-F09 | 更新时间 | 头部展示「数据更新于 xxxx-xx-xx 08:00」，超过 36 小时显示黄色提示 |
| F-F10 | 响应式 | ≥1200px 三列，768–1199px 两列，<768px 单列且粒子数量减半 |
| F-F11 | 状态处理 | 骨架屏、空收藏空态、请求失败重试按钮 |

---

## 3. 页面原型描述

### 3.1 页面结构（单页应用，仅一个主页面）

```
┌──────────────────────────────────────────────────────────────────────┐
│  粒子特效背景层（Canvas，z-index: 0，fixed 全屏）                      │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ Header（z-index: 10）                                             │ │
│ │  LOGO「Github 7 日 Star 榜」   搜索框   语言筛选▾   只看收藏⭐    │ │
│ │  数据更新于 2026-09-23 08:00 · 共收录 486 个项目                  │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │ 排序 Tab：[7日新增 ▾] [总 Star] [增速] [最新收录]                 │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │ Top 3 高亮区（3 张大卡，横向排列，移动端纵向堆叠）                │ │
│ │  ┌─────────┐ ┌─────────┐ ┌─────────┐                             │ │
│ │  │ 🥇 #1   │ │ 🥈 #2   │ │ 🥉 #3   │                             │ │
│ │  │ owner/r │ │ owner/r │ │ owner/r │                             │ │
│ │  │ 描述... │ │ 描述... │ │ 描述... │                             │ │
│ │  │ ●Python │ │ ●TypeScript││ ●Go    │                             │ │
│ │  │ ⭐128k  │ │ ⭐96.2k │ │ ⭐64.7k │                             │ │
│ │  │ ↑3421/7d│ │ ↑2890/7d│ │ ↑2301/7d│                             │ │
│ │  └─────────┘ └─────────┘ └─────────┘                             │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │ 项目卡片网格（glassmorphism 半透明卡片）                          │ │
│ │  ┌────────────────────┐ ┌────────────────────┐                   │ │
│ │  │ #4  owner/repo   ⭐│ │ #5  owner/repo   ⭐│  ...               │ │
│ │  │ 描述文本（2行截断） │ │                    │                   │ │
│ │  │ ●Python  ⭐12.3k   │ │                    │                   │ │
│ │  │ 7日 +1024 (↑8.3%)  │ │                    │                   │ │
│ │  └────────────────────┘ └────────────────────┘                   │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │ 分页器：  ‹ 1 2 3 … 25 ›        每页 [20 ▾] 条                   │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │ Footer：数据来源 Github API · 每日 08:00 更新 · 本项目开源        │ │
│ └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 关键交互说明

| 元素 | 交互 |
| --- | --- |
| 粒子背景 | 粒子缓慢漂浮、靠近鼠标时产生连线；`pointer-events: none` 不影响操作 |
| 卡片 | hover 上浮 4px、阴影增强；点击卡片主体（非星标/链接）打开详情抽屉 |
| 星标按钮 | 未收藏为描边星，已收藏为实心金色星；点击即时切换（乐观更新），接口失败回滚并 toast 提示 |
| 语言筛选 | 下拉多选，选中后自动生成胶囊标签，支持单个删除与「清空」 |
| 分页 | URL 同步 `?page=2&language=Python`，支持浏览器前进/后退 |
| 详情抽屉 | 从右侧滑入，遮罩点击/ESC 关闭，内含 7 日趋势迷你折线图 |
| 刷新提示 | Header 展示更新时间；数据陈旧（>36h）时显示黄色提示条 |

### 3.3 视觉规范

- 主色：`#0d1117`（Github 深色底）、强调色 `#58a6ff`（链接蓝）、增长色 `#3fb950`（绿）、收藏色 `#f0c419`（金）。
- 卡片：`rgba(255,255,255,0.05)` 半透明 + `backdrop-filter: blur(10px)` + 1px `rgba(255,255,255,0.1)` 边框，圆角 12px。
- 字体：系统字体栈 `-apple-system, "Segoe UI", Roboto, "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif`。
- 数字使用等宽字形，Star 数 ≥1000 时缩写为 `12.3k`。

### 3.4 异常与边界

- 无数据（首次部署未拉取）：展示空态插画 + 「立即刷新」按钮（调用 B10，需提示输入 Admin Token 或使用后端默认允许）。
- Github 配额耗尽：Header 展示黄色告警「Github API 配额受限，数据可能延迟」。
- 网络错误：列表区展示错误态 + 重试按钮。

---

## 4. 数据库表结构设计

数据库：SQLite（文件 `data/app.db`，开启 WAL 模式）。ORM：SQLAlchemy 2.0。

### 4.1 E-R 概述

```
repos (仓库主表) 1 ──< repo_snapshots (每日快照)
repos 1 ──< favorites (收藏，按 client_id 隔离)
meta_info / scheduler_lock (元数据与调度锁)
```

### 4.2 `repos` — 仓库主表

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | 内部主键 |
| `repo_id` | INTEGER | UNIQUE NOT NULL | Github 仓库 ID |
| `full_name` | TEXT | NOT NULL | `owner/repo` |
| `owner` | TEXT | NOT NULL | 所有者 |
| `name` | TEXT | NOT NULL | 仓库名 |
| `description` | TEXT | | 描述 |
| `language` | TEXT | INDEX | 主编程语言（NULL 归一化存 `'Unknown'`） |
| `html_url` | TEXT | NOT NULL | Github 地址 |
| `homepage` | TEXT | | 主页 |
| `avatar_url` | TEXT | | Owner 头像 |
| `topics` | TEXT | | JSON 数组字符串 |
| `license` | TEXT | | 许可证名称 |
| `total_stars` | INTEGER | DEFAULT 0, INDEX | 当前总 Star |
| `forks_count` | INTEGER | DEFAULT 0 | Fork 数 |
| `open_issues_count` | INTEGER | DEFAULT 0 | Open Issue 数 |
| `stars_1d` | INTEGER | DEFAULT 0 | 近 1 日新增 |
| `stars_7d` | INTEGER | DEFAULT 0, INDEX | 近 7 日新增 |
| `stars_7d_rate` | REAL | DEFAULT 0 | `stars_7d / max(total_stars - stars_7d, 1)` |
| `created_at` | TEXT | | Github 仓库创建时间（ISO8601） |
| `pushed_at` | TEXT | | 最后推送时间 |
| `repo_created_at` | TEXT | | 同 `created_at`，便于排序（避免 ORM 关键字） |
| `is_active` | INTEGER | DEFAULT 1 | 是否继续跟踪（0=停止跟踪） |
| `first_seen_at` | TEXT | NOT NULL | 首次收录时间 |
| `updated_at` | TEXT | NOT NULL | 最后更新时间 |

索引：`idx_repos_stars_7d (stars_7d DESC)`、`idx_repos_total_stars (total_stars DESC)`、`idx_repos_language (language)`、`idx_repos_lang_7d (language, stars_7d DESC)`。

### 4.3 `repo_snapshots` — 每日快照表

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | INTEGER | PK | |
| `repo_id` | INTEGER | NOT NULL, INDEX | Github 仓库 ID |
| `snapshot_date` | TEXT | NOT NULL | 快照日期 `YYYY-MM-DD` |
| `total_stars` | INTEGER | NOT NULL | 当日 Star 总数 |
| `forks_count` | INTEGER | DEFAULT 0 | |
| `open_issues_count` | INTEGER | DEFAULT 0 | |
| `delta_stars` | INTEGER | DEFAULT 0 | 相对上一快照的增量 |
| `fetched_at` | TEXT | NOT NULL | 抓取时间 |

唯一约束：`UNIQUE(repo_id, snapshot_date)`（配合 `INSERT ... ON CONFLICT DO UPDATE` 幂等写入）。

### 4.4 `favorites` — 收藏表

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | INTEGER | PK | |
| `client_id` | TEXT | NOT NULL | 客户端标识（localStorage 生成 UUID） |
| `repo_id` | INTEGER | NOT NULL | Github 仓库 ID |
| `created_at` | TEXT | NOT NULL | 收藏时间 |

唯一约束：`UNIQUE(client_id, repo_id)`；索引：`idx_fav_client (client_id)`、`idx_fav_repo (repo_id)`。

### 4.5 `meta_info` — 元数据表（KV）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `key` | TEXT PK | 如 `last_fetch_at`、`last_fetch_status`、`github_rate_remaining`、`github_rate_reset_at`、`repo_count` |
| `value` | TEXT | 值 |
| `updated_at` | TEXT | 更新时间 |

### 4.6 `scheduler_lock` — 调度锁表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_name` | TEXT PK | 任务名 |
| `locked_at` | TEXT | 加锁时间 |
| `expires_at` | TEXT | 过期时间（防止任务异常退出导致死锁） |

### 4.7 建表 SQL（摘要）

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS repos (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id           INTEGER NOT NULL UNIQUE,
  full_name         TEXT NOT NULL,
  owner             TEXT NOT NULL,
  name              TEXT NOT NULL,
  description       TEXT,
  language          TEXT,
  html_url          TEXT NOT NULL,
  homepage          TEXT,
  avatar_url        TEXT,
  topics            TEXT,
  license           TEXT,
  total_stars       INTEGER DEFAULT 0,
  forks_count       INTEGER DEFAULT 0,
  open_issues_count INTEGER DEFAULT 0,
  stars_1d          INTEGER DEFAULT 0,
  stars_7d          INTEGER DEFAULT 0,
  stars_7d_rate     REAL    DEFAULT 0,
  repo_created_at   TEXT,
  pushed_at         TEXT,
  is_active         INTEGER DEFAULT 1,
  first_seen_at     TEXT NOT NULL,
  updated_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_repos_stars_7d   ON repos(stars_7d DESC);
CREATE INDEX IF NOT EXISTS idx_repos_total      ON repos(total_stars DESC);
CREATE INDEX IF NOT EXISTS idx_repos_language   ON repos(language);
CREATE INDEX IF NOT EXISTS idx_repos_lang_7d    ON repos(language, stars_7d DESC);

CREATE TABLE IF NOT EXISTS repo_snapshots (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id           INTEGER NOT NULL,
  snapshot_date     TEXT NOT NULL,
  total_stars       INTEGER NOT NULL,
  forks_count       INTEGER DEFAULT 0,
  open_issues_count INTEGER DEFAULT 0,
  delta_stars       INTEGER DEFAULT 0,
  fetched_at        TEXT NOT NULL,
  UNIQUE(repo_id, snapshot_date)
);
CREATE INDEX IF NOT EXISTS idx_snap_repo_date ON repo_snapshots(repo_id, snapshot_date);

CREATE TABLE IF NOT EXISTS favorites (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id  TEXT NOT NULL,
  repo_id    INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(client_id, repo_id)
);
CREATE INDEX IF NOT EXISTS idx_fav_client ON favorites(client_id);
CREATE INDEX IF NOT EXISTS idx_fav_repo   ON favorites(repo_id);

CREATE TABLE IF NOT EXISTS meta_info (
  key        TEXT PRIMARY KEY,
  value      TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS scheduler_lock (
  task_name TEXT PRIMARY KEY,
  locked_at TEXT,
  expires_at TEXT
);
```

### 4.8 数据量估算

- 500 个仓库 × 90 天快照 = 45,000 行，SQLite 完全无压力，数据库文件约 10–20 MB。
- 收藏表按用户量线性增长，单用户最多 500 行。

---

## 5. 项目目录结构

```
github-star-ranking/
├── README.md
├── LICENSE
├── .env.example                      # 环境变量示例
├── .gitignore
├── .dockerignore
├── Dockerfile                        # 多阶段构建，uv 安装依赖
├── docker-compose.yml                # 单服务 + 数据卷
├── pyproject.toml                    # 项目元数据与依赖（uv 管理）
├── uv.lock                           # uv 生成的锁定文件
├── Makefile                          # 常用命令快捷方式（可选）
│
├── data/                             # 运行时数据（挂载卷）
│   └── app.db                        # SQLite 数据库文件
│
├── app/                              # 后端主包
│   ├── __init__.py
│   ├── main.py                       # FastAPI 应用入口、生命周期、挂载静态目录
│   ├── config.py                     # pydantic-settings 配置（环境变量）
│   ├── logging_config.py             # 日志配置
│   │
│   ├── api/                          # 路由层
│   │   ├── __init__.py
│   │   ├── deps.py                   # 依赖注入（DB Session、client_id、admin token 校验）
│   │   ├── response.py               # 统一响应封装与异常处理器
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py             # 聚合 v1 路由
│   │       ├── endpoints/
│   │       │   ├── repos.py          # B01/B02
│   │       │   ├── languages.py      # B03
│   │       │   ├── favorites.py      # B04-B07
│   │       │   ├── meta.py           # B08/B09/B11
│   │       │   └── admin.py          # B10
│   │
│   ├── core/
│   │   ├── constants.py              # 常量（语言色值、排序枚举等）
│   │   ├── errors.py                 # 业务异常与错误码
│   │   └── security.py               # Admin Token 校验
│   │
│   ├── db/
│   │   ├── base.py                   # DeclarativeBase
│   │   ├── session.py                # engine + SessionLocal + get_db
│   │   ├── init_db.py                # 建表、PRAGMA、初始数据
│   │   └── seed.py                   # 首次部署的可选种子数据
│   │
│   ├── models/                       # ORM 模型
│   │   ├── __init__.py
│   │   ├── repo.py                   # Repo
│   │   ├── snapshot.py               # RepoSnapshot
│   │   ├── favorite.py               # Favorite
│   │   └── meta.py                   # MetaInfo / SchedulerLock
│   │
│   ├── schemas/                      # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── common.py                 # ApiResponse / PageResult
│   │   ├── repo.py                   # RepoOut / RepoDetail / RepoQuery
│   │   ├── favorite.py
│   │   └── meta.py
│   │
│   ├── repositories/                 # 数据访问层
│   │   ├── repo_repo.py
│   │   ├── snapshot_repo.py
│   │   └── favorite_repo.py
│   │
│   ├── services/
│   │   ├── ranking_service.py        # 榜单查询、筛选、排序、分页
│   │   ├── favorite_service.py       # 收藏业务
│   │   ├── stats_service.py          # 统计聚合
│   │   └── github/
│   │       ├── client.py             # Github API 客户端（限流、重试、配额）
│   │       ├── search.py             # 候选仓库发现
│   │       ├── sync.py               # 仓库详情抓取 + 快照写入
│   │       └── delta.py              # 7 日增量计算
│   │
│   ├── tasks/
│   │   ├── scheduler.py              # APScheduler 配置与注册
│   │   └── jobs.py                   # 各定时任务实现
│   │
│   └── utils/
│       ├── time_util.py              # 时间格式化、日期推算
│       └── number_util.py            # Star 数缩写格式化
│
├── web/                              # 前端静态资源（由 FastAPI StaticFiles 托管）
│   ├── index.html
│   ├── assets/
│   │   ├── css/
│   │   │   ├── main.css              # 布局、卡片、分页
│   │   │   ├── particles.css         # 背景层样式
│   │   │   └── responsive.css        # 媒体查询
│   │   └── js/
│   │       ├── main.js               # 入口与初始化
│   │       ├── api.js                # fetch 封装（含 X-Client-Id）
│   │       ├── particles.js          # Canvas 粒子引擎
│   │       ├── components/
│   │       │   ├── repoCard.js       # 卡片渲染
│   │       │   ├── filterBar.js      # 语言/搜索/排序控件
│   │       │   ├── pagination.js     # 分页器
│   │       │   ├── favorite.js       # 收藏逻辑与 localStorage
│   │       │   ├── detailDrawer.js   # 详情抽屉 + 迷你趋势图
│   │       │   └── toast.js          # 轻提示
│   │       └── config.js             # 接口基址、常量
│   └── favicon.ico
│
├── tests/                            # pytest 测试
│   ├── conftest.py
│   ├── test_api_repos.py
│   ├── test_api_favorites.py
│   ├── test_github_delta.py
│   └── test_scheduler_jobs.py
│
└── scripts/
    ├── entrypoint.sh                 # 容器启动脚本（初始化 DB + 启动 uvicorn）
    └── init_db.py                    # 手动初始化数据库
```

---

## 6. 分阶段开发执行计划

总工期约 **15 个工作日**（单人全职投入估算）。

### 阶段一：基础骨架（Day 1–2）

| 任务 | 产出 |
| --- | --- |
| uv 初始化项目、配置 `pyproject.toml` | 可 `uv run` 启动的空白 FastAPI 服务 |
| FastAPI 应用骨架（配置、日志、统一响应、异常处理） | `app/main.py`、`config.py`、`response.py` |
| SQLite 引擎与 ORM 模型、建表脚本 | `app/db/*`、`app/models/*` |
| 健康检查接口 `/api/v1/health` | 可用 curl 验证 |

**验收标准**：`uv run uvicorn app.main:app` 启动成功，`/api/v1/health` 返回 `{"code":0}`，数据库文件生成且表结构正确。

### 阶段二：Github 数据采集（Day 3–5）

| 任务 | 产出 |
| --- | --- |
| Github API 客户端（重试、限流、配额记录） | `services/github/client.py` |
| 候选仓库发现（Search API） | `services/github/search.py` |
| 仓库详情抓取 + 快照写入（幂等 upsert） | `services/github/sync.py` |
| 7 日增量计算 | `services/github/delta.py` |
| 定时任务接入 APScheduler | `tasks/*` |
| 管理端手动触发接口 | `api/v1/endpoints/admin.py` |

**验收标准**：运行一次 `POST /api/v1/admin/refresh`，数据库写入 ≥300 个仓库与对应快照；连续模拟 8 天数据后 `stars_7d` 计算准确（可用 `scripts/` 下的造数脚本验证）。

### 阶段三：业务接口（Day 6–7）

| 任务 | 产出 |
| --- | --- |
| 榜单列表接口（分页、筛选、排序、搜索） | `endpoints/repos.py` |
| 项目详情 + 趋势接口 | 同上 |
| 语言列表 / 统计接口 | `endpoints/languages.py`、`meta.py` |
| 收藏全套接口 | `endpoints/favorites.py` |
| pytest 用例覆盖核心接口 | `tests/*` |

**验收标准**：所有接口通过 Postman/curl 验证，边界参数（page 越界、空语言、非法排序字段）返回合理；`pytest` 全部通过。

### 阶段四：前端页面（Day 8–11）

| 任务 | 产出 |
| --- | --- |
| 页面骨架 + Header + 粒子背景引擎 | `index.html`、`particles.js` |
| 卡片列表渲染 + Top3 高亮 | `repoCard.js` |
| 筛选栏（语言多选、搜索、排序 Tab） | `filterBar.js` |
| 分页器 + URL 状态同步 | `pagination.js` |
| 收藏交互 + 只看收藏 | `favorite.js` |
| 详情抽屉 + 迷你趋势图 | `detailDrawer.js` |
| 响应式与状态（骨架屏/空态/错误态） | `responsive.css` |

**验收标准**：桌面/移动端浏览正常；翻页、筛选、收藏、搜索全链路可用；Lighthouse 性能 ≥85；关闭 JS 粒子降级正常。

### 阶段五：容器化与部署（Day 12–13）

| 任务 | 产出 |
| --- | --- |
| 编写 Dockerfile（uv 多阶段构建） | `Dockerfile` |
| 编写 docker-compose.yml（卷挂载、环境变量、健康检查） | `docker-compose.yml` |
| 容器启动脚本、静态资源挂载 | `scripts/entrypoint.sh` |
| 本地 `docker compose up` 验证 | 可访问 `http://localhost:8000` |

**验收标准**：`docker compose up -d --build` 后页面可访问、数据卷持久化、容器重启后数据不丢失。

### 阶段六：联调、打磨与文档（Day 14–15）

| 任务 | 产出 |
| --- | --- |
| 全链路联调与性能排查（SQLite 索引、N+1） | 优化记录 |
| 异常场景验证（Github 403/429、DB 锁、慢网） | 测试用例 |
| README 部署说明、环境变量说明 | `README.md`、`.env.example` |
| 数据备份方案（SQLite 定期 copy / `VACUUM INTO`） | 备份脚本 |

**验收标准**：完整回归通过，README 可指导第三方一键部署。

### 里程碑汇总

| 里程碑 | 时间点 | 交付物 |
| --- | --- | --- |
| M1 骨架可运行 | Day 2 | 可启动的 FastAPI 服务 + 数据库 |
| M2 数据链路打通 | Day 5 | 定时任务产出真实榜单数据 |
| M3 接口完备 | Day 7 | 全部 API 可用并有测试 |
| M4 前端可用 | Day 11 | 完整交互的网页 |
| M5 可部署 | Day 13 | Docker 镜像可运行 |
| M6 发布 | Day 15 | 正式版本 + 文档 |

---

## 7. 部署方案

### 7.1 部署架构

```
浏览器 ──HTTP──> [ Docker 容器: gh-star-ranking ]
                   ├── Uvicorn (workers=1) + FastAPI
                   │     ├── /api/v1/*  REST 接口
                   │     └── /          静态页面 (web/)
                   ├── APScheduler（进程内定时拉取 Github API）
                   └── SQLite 文件 (挂载卷 /app/data/app.db)
                             ↕
                      Github Official API (api.github.com)
```

单机单容器部署，无需 Redis / Nginx（生产环境可在前置反向代理层加 HTTPS 与压缩）。

### 7.2 环境变量（`.env`）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_ENV` | `production` | 运行环境 |
| `APP_HOST` | `0.0.0.0` | 监听地址 |
| `APP_PORT` | `8000` | 监听端口 |
| `APP_WORKERS` | `1` | Uvicorn worker 数（SQLite 场景固定为 1） |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/app.db` | 数据库连接串 |
| `GITHUB_TOKEN` | 空 | Github Personal Access Token（可选，强烈建议配置） |
| `GITHUB_API_BASE` | `https://api.github.com` | API 基址 |
| `GITHUB_REQUEST_INTERVAL` | `0.7` | 请求间隔秒数 |
| `GITHUB_MAX_REPOS` | `500` | 候选池上限 |
| `GITHUB_RATE_LIMIT_THRESHOLD` | `50` | 配额低于该值停止抓取 |
| `FETCH_CRON_HOUR` | `0` | 每日快照 UTC 小时 |
| `DISCOVER_CRON_HOUR` | `23` | 候选发现 UTC 小时（前一天 23:30 对应北京 07:30） |
| `DELTA_CRON_HOUR` | `1` | 增量计算 UTC 小时 |
| `TZ` | `Asia/Shanghai` | 容器时区 |
| `ADMIN_TOKEN` | 必填 | 管理接口鉴权 Token |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `SNAPSHOT_RETENTION_DAYS` | `90` | 快照保留天数 |
| `CORS_ORIGINS` | `*` | 允许来源 |

### 7.3 `pyproject.toml`（uv 管理）

```toml
[project]
name = "github-star-ranking"
version = "0.1.0"
description = "Github 7 日新增 Star 项目榜单系统"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy>=2.0.36",
    "aiosqlite>=0.20.0",
    "alembic>=1.14.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "httpx>=0.28.0",
    "apscheduler>=3.10.4",
    "python-dotenv>=1.0.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
package = false              # 以应用模式管理依赖，不打包发布
dev-dependencies = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.8.0",
]

[tool.uv.pip]
# 如需私有源，可在此配置 index-url

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### 7.4 Dockerfile（多阶段 + uv）

```dockerfile
# ---------- Stage 1: 依赖构建 ----------
FROM ghcr.io/astral-sh/uv:0.5-python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# 先复制依赖声明，最大化缓存命中
COPY pyproject.toml uv.lock ./

# 只安装依赖到独立 venv（--no-install-project：跳过项目自身安装）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# ---------- Stage 2: 运行 ----------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser \
    && apt-get update \
    && apt-get install -y --no-install-recommends tzdata curl \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制已装好的虚拟环境
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# 复制应用代码
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser web ./web
COPY --chown=appuser:appuser pyproject.toml README.md ./
COPY --chown=appuser:appuser scripts ./scripts

# 数据与日志目录（由卷挂载）
RUN mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["/app/.venv/bin/uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

> 说明：
> - 使用官方 `ghcr.io/astral-sh/uv` 镜像，`uv sync --frozen` 依据 `uv.lock` 精确安装。
> - 若希望容器内也能 `uv run`，可将 runtime 阶段的 `CMD` 改为 `["uv", "run", "uvicorn", ...]` 并在 runtime 镜像中安装 uv（`COPY --from=uv:latest /uv /usr/local/bin/uv`）。当前方案为「构建期用 uv、运行期直接用 venv」，启动更快、镜像更小。

### 7.5 docker-compose.yml

```yaml
services:
  gh-star-ranking:
    build:
      context: .
      dockerfile: Dockerfile
    image: gh-star-ranking:0.1.0
    container_name: gh-star-ranking
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      APP_ENV: production
      APP_HOST: 0.0.0.0
      APP_PORT: 8000
      APP_WORKERS: 1
      TZ: Asia/Shanghai
      LOG_LEVEL: INFO
      DATABASE_URL: sqlite+aiosqlite:////app/data/app.db
      GITHUB_TOKEN: ${GITHUB_TOKEN:-}
      GITHUB_REQUEST_INTERVAL: "0.7"
      GITHUB_MAX_REPOS: "500"
      GITHUB_RATE_LIMIT_THRESHOLD: "50"
      FETCH_CRON_HOUR: "0"
      DELTA_CRON_HOUR: "1"
      ADMIN_TOKEN: ${ADMIN_TOKEN:?ADMIN_TOKEN is required}
      SNAPSHOT_RETENTION_DAYS: "90"
      CORS_ORIGINS: "*"
    volumes:
      - gh-star-data:/app/data          # SQLite 持久化
      - gh-star-logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  gh-star-data:
    driver: local
  gh-star-logs:
    driver: local
```

### 7.6 启动与运维命令

```bash
# 1) 准备环境变量
cp .env.example .env
# 编辑 .env，填写 GITHUB_TOKEN 与 ADMIN_TOKEN

# 2) 构建并启动
docker compose up -d --build

# 3) 查看日志
docker compose logs -f gh-star-ranking

# 4) 首次立即拉取数据（不等定时任务）
curl -X POST http://localhost:8000/api/v1/admin/refresh \
     -H "X-Admin-Token: <ADMIN_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"force": true}'

# 5) 停止 / 更新
docker compose down
docker compose pull && docker compose up -d

# 6) 本地开发（uv）
uv sync                       # 安装依赖
uv run uvicorn app.main:app --reload --port 8000
uv run pytest                 # 运行测试
uv run ruff check .           # 代码检查
```

### 7.7 数据备份与迁移

- 备份：容器内定时执行 `sqlite3 /app/data/app.db "VACUUM INTO '/app/data/backup/app_$(date +%F).db'"`，或直接打包 `gh-star-data` 卷。
- 建议每周备份一次并保留 4 份。
- 迁移：复制 `app.db` 文件至新机器同名卷目录即可，无需额外迁移工具。

### 7.8 监控与告警（建议）

- 容器 `HEALTHCHECK` + Docker `restart: unless-stopped` 保证进程存活。
- 应用内记录 `last_fetch_status`（`success` / `partial` / `failed`）与 `github_rate_remaining`，在 `/api/v1/meta/stats` 暴露，便于外部探活。
- 生产建议在宿主机加一个 cron，检测 `/api/v1/health` 失败时发告警。

### 7.9 安全与合规

- `ADMIN_TOKEN` 强制必填，管理接口仅接受 Header 传入，不写入日志。
- `GITHUB_TOKEN` 仅用于只读 public 数据，建议使用 fine-grained token，最小权限（public repositories read-only）。
- 不存储任何用户个人身份信息，`client_id` 仅为随机 UUID，用户可自行清除 `localStorage` 重置。
- 容器内以非 root 用户运行。
- 建议生产环境在前置 Nginx/Traefik 配置 HTTPS 与基础限流。

---

## 附录 A：Github 数据字段映射

| Github API 字段 | 本地字段 | 说明 |
| --- | --- | --- |
| `id` | `repo_id` | 仓库唯一 ID |
| `full_name` | `full_name` | `owner/repo` |
| `description` | `description` | 描述 |
| `language` | `language` | 主语言，NULL → `Unknown` |
| `stargazers_count` | `total_stars` | 总 Star 数 |
| `forks_count` | `forks_count` | |
| `open_issues_count` | `open_issues_count` | |
| `html_url` | `html_url` | |
| `homepage` | `homepage` | |
| `owner.avatar_url` | `avatar_url` | |
| `topics` | `topics` | JSON 序列化 |
| `license.name` | `license` | |
| `created_at` | `repo_created_at` | |
| `pushed_at` | `pushed_at` | |

## 附录 B：7 日增量计算逻辑

```text
stars_7d = total_stars(今日快照) - total_stars(今日 - 7 天的最近一条快照)
stars_1d = total_stars(今日快照) - total_stars(昨日快照)
stars_7d_rate = stars_7d / max(total_stars - stars_7d, 1)
```

- 若 7 天前不存在快照（新收录仓库），取**最早**一条快照作为基线，并标记 `partial = true`，排序时 `stars_7d` 仍参与但不展示高置信标识。
- 若基线快照的 `total_stars` 大于当前值（用户取消 Star / 仓库重建），`stars_7d` 取 `max(delta, 0)`。

## 附录 C：常见风险与对策

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| Github API 配额耗尽 | 数据不更新 | Token 认证（5000/h）；阈值中断 + 保留已抓数据；分多日补齐 |
| Search API 结果不稳定 | 候选池波动 | 候选池做持久化累积，不因单日缺失而剔除 |
| 快照缺失导致增量偏差 | 榜单不准 | 基线回退取最近快照 + `partial` 标记 |
| SQLite 并发写锁 | 接口超时 | 单 worker；`WAL` + `busy_timeout=5000`；写操作串行批处理 |
| 定时任务重复执行 | 数据重复/配额浪费 | `scheduler_lock` 表 + 单副本部署 |
| 粒子特效性能问题 | 低端设备卡顿 | 粒子数自适应（按屏幕面积与 DPR）；`visibilitychange` 暂停；支持开关 |
