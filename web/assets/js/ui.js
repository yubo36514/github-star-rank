/**
 * UI 组件与工具函数：卡片渲染、分页器、骨架屏、Toast、趋势图。
 */

/** HTML 转义，防止简介中的特殊字符破坏结构 */
export function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/** 数字千分位格式化 */
export function formatNumber(value) {
    if (typeof value !== 'number') return '0';
    return value.toLocaleString('en-US');
}

/** 百分比格式化（入参为 0.0275 -> 2.75%） */
export function formatPercent(value) {
    if (typeof value !== 'number') return '0%';
    return `${(value * 100).toFixed(2)}%`;
}

/**
 * 创建一个项目卡片。
 * 需求：点击卡片跳转 Github 项目地址；星标按钮用于收藏；「趋势」按钮打开详情抽屉。
 * @param {Object} repo 后端返回的仓库数据
 * @param {Object} handlers { onToggleFavorite, onShowDetail }
 */
export function createRepoCard(repo, handlers = {}) {
    const card = document.createElement('article');
    card.className = `repo-card${repo.rank <= 3 ? ' is-top' : ''}`;
    card.dataset.repoId = String(repo.repo_id);

    const rankClass = repo.rank === 1 ? 'rank-1' : repo.rank === 2 ? 'rank-2' : repo.rank === 3 ? 'rank-3' : '';
    const description = repo.description || '暂无简介';
    const language = repo.language || 'Unknown';

    card.innerHTML = `
        <div class="card-head">
            <span class="rank-badge ${rankClass}">#${repo.rank}</span>
            <button class="fav-btn ${repo.is_favorite ? 'is-fav' : ''}" type="button"
                    title="${repo.is_favorite ? '取消收藏' : '收藏'}"
                    aria-label="收藏">${repo.is_favorite ? '★' : '☆'}</button>
        </div>
        <a class="repo-title" href="${escapeHtml(repo.html_url)}" target="_blank" rel="noreferrer">
            <span class="owner">${escapeHtml(repo.owner)}/</span>${escapeHtml(repo.name)}
        </a>
        <p class="repo-desc">${escapeHtml(description)}</p>
        <div class="card-meta">
            <span class="lang-tag">
                <i class="lang-dot" style="background:${escapeHtml(repo.language_color || '#8b949e')}"></i>
                ${escapeHtml(language)}
            </span>
            <span title="总 Star 数">★ ${escapeHtml(repo.total_stars_text || formatNumber(repo.total_stars))}</span>
            <span class="growth" title="近 7 日新增 Star">↑ ${formatNumber(repo.stars_7d)} / 7d</span>
            <span class="growth-rate" title="近 7 日增长率">${formatPercent(repo.stars_7d_rate)}</span>
        </div>
        <div class="card-footer">
            <span title="今日新增">今日 +${formatNumber(repo.stars_1d)}${repo.is_partial ? ' · 估算' : ''}</span>
            <button class="trend-btn" type="button">趋势</button>
        </div>
    `;

    // 点击卡片主体：跳转 Github 项目地址
    card.addEventListener('click', () => {
        window.open(repo.html_url, '_blank', 'noopener');
    });

    // 收藏按钮：阻止冒泡，避免同时触发跳转
    const favBtn = card.querySelector('.fav-btn');
    favBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        handlers.onToggleFavorite && handlers.onToggleFavorite(repo, favBtn);
    });

    // 趋势按钮：打开详情抽屉
    const trendBtn = card.querySelector('.trend-btn');
    trendBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        handlers.onShowDetail && handlers.onShowDetail(repo);
    });

    return card;
}

/** 渲染骨架屏 */
export function renderSkeletons(container, count = 6) {
    container.innerHTML = '';
    for (let i = 0; i < count; i += 1) {
        const skeleton = document.createElement('div');
        skeleton.className = 'skeleton';
        container.appendChild(skeleton);
    }
}

/**
 * 渲染分页器（首页 / 末页 / 当前页附近页码）。
 * @param {HTMLElement} container 分页容器
 * @param {Object} info { page, totalPages }
 * @param {Function} onPageChange 点击回调
 */
export function renderPagination(container, info, onPageChange) {
    const { page, totalPages } = info;
    container.innerHTML = '';
    if (!totalPages || totalPages <= 1) return;

    const createButton = (label, targetPage, options = {}) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `page-btn${options.active ? ' is-active' : ''}`;
        button.textContent = label;
        if (options.disabled) button.disabled = true;
        button.addEventListener('click', () => onPageChange(targetPage));
        return button;
    };

    container.appendChild(createButton('‹', page - 1, { disabled: page <= 1 }));

    const pages = new Set([1, totalPages, page - 1, page, page + 1]);
    const sortedPages = [...pages].filter((p) => p >= 1 && p <= totalPages).sort((a, b) => a - b);

    let lastPage = 0;
    sortedPages.forEach((p) => {
        if (lastPage && p - lastPage > 1) {
            const ellipsis = document.createElement('span');
            ellipsis.className = 'page-ellipsis';
            ellipsis.textContent = '…';
            container.appendChild(ellipsis);
        }
        container.appendChild(createButton(String(p), p, { active: p === page }));
        lastPage = p;
    });

    container.appendChild(createButton('›', page + 1, { disabled: page >= totalPages }));
}

/** 轻提示 */
export function toast(message, type = 'info', duration = 2600) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const item = document.createElement('div');
    item.className = `toast${type === 'error' ? ' is-error' : type === 'success' ? ' is-success' : ''}`;
    item.textContent = message;
    container.appendChild(item);
    setTimeout(() => item.remove(), duration);
}

/**
 * 生成趋势折线图（内联 SVG，不依赖图表库）。
 * @param {Array} trend [{date, total_stars, delta}]
 */
export function buildTrendChart(trend) {
    if (!trend || trend.length === 0) return '<p class="repo-desc">暂无趋势数据</p>';

    const width = 400;
    const height = 130;
    const padding = 10;
    const values = trend.map((item) => item.total_stars);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = Math.max(max - min, 1);

    const points = trend.map((item, index) => {
        const x = padding + (index * (width - padding * 2)) / Math.max(trend.length - 1, 1);
        const y = height - padding - ((item.total_stars - min) / span) * (height - padding * 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    });

    const areaPoints = `${padding},${height - padding} ${points.join(' ')} ${width - padding},${height - padding}`;
    const last = trend[trend.length - 1];

    return `
        <svg class="trend-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
            <defs>
                <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#58a6ff" stop-opacity="0.35" />
                    <stop offset="100%" stop-color="#58a6ff" stop-opacity="0" />
                </linearGradient>
            </defs>
            <polygon points="${areaPoints}" fill="url(#trendFill)" />
            <polyline points="${points.join(' ')}" fill="none" stroke="#58a6ff" stroke-width="2" stroke-linejoin="round" />
        </svg>
        <div class="card-meta" style="margin-top:6px">
            <span>起点 ${formatNumber(trend[0].total_stars)}</span>
            <span>最新 ${formatNumber(last.total_stars)}</span>
            <span class="growth">7 日区间 +${formatNumber(last.total_stars - trend[0].total_stars)}</span>
        </div>
    `;
}
