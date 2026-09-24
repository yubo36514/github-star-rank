/**
 * 项目详情抽屉：展示仓库信息 + 近 8 日 Star 趋势图。
 */

import { fetchRepoDetail } from './api.js';
import { buildTrendChart, escapeHtml, formatNumber, formatPercent, toast } from './ui.js';

const drawer = () => document.getElementById('drawer');
const mask = () => document.getElementById('drawer-mask');
const body = () => document.getElementById('drawer-body');

/** 关闭抽屉 */
export function closeDrawer() {
    const el = drawer();
    const maskEl = mask();
    if (el) el.hidden = true;
    if (maskEl) maskEl.hidden = true;
}

/** 打开抽屉并加载详情 */
export async function openDrawer(repo) {
    const el = drawer();
    const maskEl = mask();
    if (!el || !maskEl) return;

    el.hidden = false;
    maskEl.hidden = false;
    body().innerHTML = '<div class="skeleton" style="height:260px"></div>';

    try {
        const detail = await fetchRepoDetail(repo.repo_id);
        render(detail);
    } catch (error) {
        body().innerHTML = `<p class="repo-desc">加载失败：${escapeHtml(error.message)}</p>`;
        toast('详情加载失败', 'error');
    }
}

function render(detail) {
    const { repo, trend } = detail;
    const topics = (repo.topics || [])
        .slice(0, 8)
        .map((topic) => `<span class="chip">${escapeHtml(topic)}</span>`)
        .join('');

    body().innerHTML = `
        <h3 class="repo-title" style="font-size:17px">${escapeHtml(repo.full_name)}</h3>
        <p class="repo-desc" style="min-height:auto">${escapeHtml(repo.description || '暂无简介')}</p>
        <div class="card-meta" style="margin-bottom:14px">
            <span class="lang-tag">
                <i class="lang-dot" style="background:${escapeHtml(repo.language_color)}"></i>${escapeHtml(repo.language)}
            </span>
            <span>★ ${escapeHtml(repo.total_stars_text)}</span>
            <span>🍴 ${formatNumber(repo.forks_count)}</span>
            <span>⚠ ${formatNumber(repo.open_issues_count)}</span>
        </div>
        <div style="margin-bottom:14px">${topics}</div>

        <div class="kv-row"><span>7 日新增</span><span class="growth">+${formatNumber(repo.stars_7d)}</span></div>
        <div class="kv-row"><span>7 日增长率</span><span>${formatPercent(repo.stars_7d_rate)}</span></div>
        <div class="kv-row"><span>今日新增</span><span>+${formatNumber(repo.stars_1d)}</span></div>
        <div class="kv-row"><span>创建时间</span><span>${escapeHtml((repo.repo_created_at || '').slice(0, 10))}</span></div>
        <div class="kv-row"><span>最近推送</span><span>${escapeHtml((repo.pushed_at || '').slice(0, 10))}</span></div>
        <div class="kv-row"><span>License</span><span>${escapeHtml(repo.license || '-')}</span></div>

        <h4 class="section-title" style="margin-top:18px">近 8 日 Star 趋势</h4>
        ${buildTrendChart(trend)}

        <a class="btn-primary" style="margin-top:18px;justify-content:center"
           href="${escapeHtml(repo.html_url)}" target="_blank" rel="noreferrer">
            在 Github 打开
        </a>
    `;
}

/** 绑定抽屉关闭事件（遮罩点击 / 按钮 / ESC） */
export function bindDrawerEvents() {
    document.getElementById('drawer-close')?.addEventListener('click', closeDrawer);
    mask()?.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closeDrawer();
    });
}
