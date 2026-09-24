/**
 * 页面主控制器：状态管理 + 数据加载 + 交互绑定。
 * 页面只通过 RESTful 接口获取数据，不依赖任何后端模板。
 */

import {
    addFavorite,
    fetchLanguages,
    fetchRepos,
    fetchStats,
    refreshData,
    removeFavorite,
} from './api.js';
import { bindDrawerEvents, openDrawer } from './drawer.js';
import { initParticles } from './particles.js';
import {
    createRepoCard,
    escapeHtml,
    formatNumber,
    renderPagination,
    renderSkeletons,
    toast,
} from './ui.js';

/* ------------------------- 页面状态 ------------------------- */
const state = {
    page: 1,
    pageSize: 20,
    languages: [], // 多选
    keyword: '',
    sortBy: 'stars_7d',
    order: 'desc',
    onlyFavorites: false,
    total: 0,
    totalPages: 1,
    loading: false,
};

const dom = {
    cardGrid: () => document.getElementById('card-grid'),
    top3Section: () => document.getElementById('top3-section'),
    top3Grid: () => document.getElementById('top3-grid'),
    pagination: () => document.getElementById('pagination'),
    emptyState: () => document.getElementById('empty-state'),
    resultCount: () => document.getElementById('result-count'),
    headerMeta: () => document.getElementById('header-meta'),
    footerMeta: () => document.getElementById('footer-meta'),
    noticeBar: () => document.getElementById('notice-bar'),
    langList: () => document.getElementById('lang-list'),
    langPanel: () => document.getElementById('lang-panel'),
    langBtnText: () => document.getElementById('lang-btn-text'),
    searchInput: () => document.getElementById('search-input'),
};

/* ------------------------- URL 同步 ------------------------- */

/** 把筛选条件写入地址栏，支持刷新/分享 */
function syncUrl() {
    const params = new URLSearchParams();
    if (state.page > 1) params.set('page', String(state.page));
    if (state.pageSize !== 20) params.set('page_size', String(state.pageSize));
    if (state.languages.length) params.set('language', state.languages.join(','));
    if (state.keyword) params.set('keyword', state.keyword);
    if (state.sortBy !== 'stars_7d') params.set('sort_by', state.sortBy);
    if (state.onlyFavorites) params.set('only_favorites', '1');
    const query = params.toString();
    const url = `${window.location.pathname}${query ? `?${query}` : ''}`;
    window.history.replaceState({}, '', url);
}

/** 从地址栏恢复筛选条件 */
function restoreFromUrl() {
    const params = new URLSearchParams(window.location.search);
    state.page = Math.max(parseInt(params.get('page') || '1', 10) || 1, 1);
    state.pageSize = parseInt(params.get('page_size') || '20', 10) || 20;
    state.languages = (params.get('language') || '').split(',').filter(Boolean);
    state.keyword = params.get('keyword') || '';
    state.sortBy = params.get('sort_by') || 'stars_7d';
    state.onlyFavorites = params.get('only_favorites') === '1';
}

/* ------------------------- 数据加载 ------------------------- */

/** 加载榜单列表并渲染 */
async function loadList(options = {}) {
    if (state.loading) return;
    state.loading = true;

    if (options.skeleton !== false) {
        renderSkeletons(dom.cardGrid(), state.pageSize > 20 ? 9 : 6);
    }

    const params = {
        page: state.page,
        page_size: state.pageSize,
        sort_by: state.sortBy,
        order: state.order,
    };
    if (state.languages.length) params.language = state.languages.join(',');
    if (state.keyword) params.keyword = state.keyword;
    if (state.onlyFavorites) params.only_favorites = true;

    try {
        const data = await fetchRepos(params);
        state.total = data.total;
        state.totalPages = data.total_pages;
        renderList(data);
        syncUrl();
    } catch (error) {
        dom.cardGrid().innerHTML = '';
        showNotice(`加载失败：${error.message}`, true);
        toast(error.message, 'error');
    } finally {
        state.loading = false;
    }
}

/** 渲染列表（Top3 + 卡片网格 + 分页） */
function renderList(data) {
    const items = data.items || [];
    const showTop3 =
        state.page === 1 &&
        !state.keyword &&
        state.languages.length === 0 &&
        state.sortBy === 'stars_7d' &&
        !state.onlyFavorites &&
        items.length >= 3;

    const top3Section = dom.top3Section();
    const top3Grid = dom.top3Grid();
    const grid = dom.cardGrid();

    grid.innerHTML = '';
    top3Grid.innerHTML = '';
    top3Section.hidden = !showTop3;

    const handlers = {
        onToggleFavorite: toggleFavorite,
        onShowDetail: (repo) => openDrawer(repo),
    };

    if (showTop3) {
        items.slice(0, 3).forEach((repo) => top3Grid.appendChild(createRepoCard(repo, handlers)));
        items.slice(3).forEach((repo) => grid.appendChild(createRepoCard(repo, handlers)));
    } else {
        items.forEach((repo) => grid.appendChild(createRepoCard(repo, handlers)));
    }

    const isEmpty = items.length === 0;
    dom.emptyState().hidden = !isEmpty;
    dom.resultCount().textContent = isEmpty ? '' : `共 ${formatNumber(state.total)} 个项目`;

    renderPagination(dom.pagination(), { page: state.page, totalPages: state.totalPages }, (page) => {
        state.page = page;
        loadList();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    if (data.updated_at) {
        dom.headerMeta().textContent = `数据更新于 ${data.updated_at}`;
    }
}

/** 加载语言筛选列表 */
async function loadLanguages() {
    try {
        const languages = await fetchLanguages();
        const list = dom.langList();
        list.innerHTML = '';
        languages.forEach((item) => {
            const label = document.createElement('label');
            label.className = 'lang-option';
            label.innerHTML = `
                <input type="checkbox" value="${escapeHtml(item.name)}"
                       ${state.languages.includes(item.name) ? 'checked' : ''} />
                <i class="lang-dot" style="background:${escapeHtml(item.color)}"></i>
                <span>${escapeHtml(item.name)}</span>
                <span class="lang-count">${item.count}</span>
            `;
            label.querySelector('input').addEventListener('change', () => {
                state.languages = [...list.querySelectorAll('input:checked')].map((el) => el.value);
                state.page = 1;
                updateLangButton();
                loadList();
            });
            list.appendChild(label);
        });
        updateLangButton();
    } catch (error) {
        console.warn('语言列表加载失败', error);
    }
}

/** 加载全局统计（收录数量、更新时间、Github 配额） */
async function loadStats() {
    try {
        const stats = await fetchStats();
        dom.headerMeta().textContent = stats.last_fetch_at
            ? `共收录 ${formatNumber(stats.repo_count)} 个项目 · 更新于 ${stats.last_fetch_at}`
            : `共收录 ${formatNumber(stats.repo_count)} 个项目 · 尚未抓取真实数据`;

        dom.footerMeta().textContent = `快照 ${formatNumber(stats.snapshot_count)} 条`;

        // Github 配额告警
        if (stats.github_rate_remaining >= 0 && stats.github_rate_remaining <= 50) {
            showNotice(`Github API 配额剩余 ${stats.github_rate_remaining}，数据更新可能延迟`, false);
        } else if (stats.last_fetch_status === 'failed') {
            showNotice('最近一次数据抓取失败，请查看服务端日志', true);
        } else {
            hideNotice();
        }
    } catch (error) {
        console.warn('统计信息加载失败', error);
    }
}

/* ------------------------- 收藏 ------------------------- */

/** 切换收藏（乐观更新，失败回滚） */
async function toggleFavorite(repo, button) {
    const nextState = !button.classList.contains('is-fav');
    button.classList.toggle('is-fav', nextState);
    button.textContent = nextState ? '★' : '☆';

    try {
        if (nextState) {
            await addFavorite(repo.repo_id);
            toast('已加入收藏', 'success');
        } else {
            await removeFavorite(repo.repo_id);
            toast('已取消收藏');
        }
    } catch (error) {
        // 回滚 UI
        button.classList.toggle('is-fav', !nextState);
        button.textContent = !nextState ? '★' : '☆';
        toast(error.message, 'error');
    }
}

/* ------------------------- 提示条 ------------------------- */
function showNotice(message, isError = false) {
    const bar = dom.noticeBar();
    bar.hidden = false;
    bar.textContent = message;
    bar.classList.toggle('is-error', isError);
}

function hideNotice() {
    dom.noticeBar().hidden = true;
}

/* ------------------------- 事件绑定 ------------------------- */

function updateLangButton() {
    const text = dom.langBtnText();
    if (!text) return;
    text.textContent = state.languages.length === 0
        ? '全部语言'
        : state.languages.length === 1
            ? state.languages[0]
            : `已选 ${state.languages.length} 种语言`;
}

function bindEvents() {
    // 语言下拉
    const langBtn = document.getElementById('lang-btn');
    langBtn?.addEventListener('click', (event) => {
        event.stopPropagation();
        dom.langPanel().hidden = !dom.langPanel().hidden;
    });
    document.addEventListener('click', () => {
        dom.langPanel().hidden = true;
    });
    dom.langPanel()?.addEventListener('click', (event) => event.stopPropagation());
    document.getElementById('lang-clear')?.addEventListener('click', () => {
        state.languages = [];
        state.page = 1;
        updateLangButton();
        loadList();
    });

    // 关键词搜索（300ms 防抖）
    let searchTimer = null;
    dom.searchInput()?.addEventListener('input', (event) => {
        clearTimeout(searchTimer);
        const value = event.target.value.trim();
        searchTimer = setTimeout(() => {
            state.keyword = value;
            state.page = 1;
            loadList();
        }, 300);
    });

    // 排序切换
    document.querySelectorAll('.sort-tab').forEach((tab) => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.sort-tab').forEach((t) => t.classList.remove('is-active'));
            tab.classList.add('is-active');
            state.sortBy = tab.dataset.sort;
            state.page = 1;
            loadList();
        });
    });

    // 每页条数
    document.getElementById('page-size')?.addEventListener('change', (event) => {
        state.pageSize = parseInt(event.target.value, 10) || 20;
        state.page = 1;
        loadList();
    });

    // 只看收藏
    const favFilterBtn = document.getElementById('fav-filter-btn');
    favFilterBtn?.addEventListener('click', () => {
        state.onlyFavorites = !state.onlyFavorites;
        state.page = 1;
        favFilterBtn.classList.toggle('is-active', state.onlyFavorites);
        loadList();
    });

    // 手动刷新数据
    const refreshBtn = document.getElementById('refresh-btn');
    refreshBtn?.addEventListener('click', async () => {
        refreshBtn.disabled = true;
        const originalText = refreshBtn.textContent;
        refreshBtn.textContent = '刷新中…';
        try {
            await refreshData(true);
            toast('刷新任务已启动，约 1-3 分钟后数据更新', 'success');
            setTimeout(() => {
                loadStats();
                loadList({ skeleton: false });
            }, 5000);
        } catch (error) {
            if (error.message !== '已取消') toast(error.message, 'error');
        } finally {
            refreshBtn.disabled = false;
            refreshBtn.textContent = originalText;
        }
    });

    bindDrawerEvents();
}

/* ------------------------- 启动 ------------------------- */

function applyStateToControls() {
    dom.searchInput().value = state.keyword;
    document.getElementById('page-size').value = String(state.pageSize);
    document.querySelectorAll('.sort-tab').forEach((tab) => {
        tab.classList.toggle('is-active', tab.dataset.sort === state.sortBy);
    });
    document.getElementById('fav-filter-btn').classList.toggle('is-active', state.onlyFavorites);
}

async function bootstrap() {
    initParticles(); // 背景粒子特效
    bindEvents();
    restoreFromUrl();
    applyStateToControls();
    await Promise.all([loadLanguages(), loadStats()]);
    await loadList();
}

bootstrap();
