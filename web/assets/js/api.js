/**
 * 接口请求封装：
 * - 统一拼接 API_BASE + /api/v1
 * - 自动带上 X-Client-Id（收藏功能用，无需登录）
 * - 统一解析 { code, message, data } 结构并抛出友好错误
 */

import { API_BASE, API_PREFIX, CLIENT_ID_KEY, REQUEST_TIMEOUT } from './config.js';

/**
 * 获取（或首次生成）客户端唯一标识。
 * 生成后保存在 localStorage 中，用户清除浏览器数据即等于重置收藏。
 */
export function getClientId() {
    let clientId = localStorage.getItem(CLIENT_ID_KEY);
    if (!clientId) {
        clientId = (crypto.randomUUID && crypto.randomUUID()) || `c-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        localStorage.setItem(CLIENT_ID_KEY, clientId);
    }
    return clientId;
}

/** 构造完整 URL（自动拼接查询参数） */
function buildUrl(path, params) {
    const url = new URL(API_BASE + API_PREFIX + path, window.location.origin);
    Object.entries(params || {}).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') return;
        url.searchParams.set(key, value);
    });
    return url.toString();
}

/**
 * 统一请求入口。
 * @param {string} path 接口路径，如 /repos
 * @param {Object} options { method, params, body, adminToken }
 * @returns {Promise<any>} 响应中的 data 字段
 */
export async function request(path, options = {}) {
    const { method = 'GET', params, body, adminToken } = options;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

    const headers = { 'X-Client-Id': getClientId() };
    if (body) headers['Content-Type'] = 'application/json';
    if (adminToken) headers['X-Admin-Token'] = adminToken;

    try {
        const response = await fetch(buildUrl(path, params), {
            method,
            headers,
            body: body ? JSON.stringify(body) : undefined,
            signal: controller.signal,
        });

        const payload = await response.json().catch(() => null);
        if (!response.ok || !payload || payload.code !== 0) {
            const message = (payload && payload.message) || `请求失败（HTTP ${response.status}）`;
            throw new Error(message);
        }
        return payload.data;
    } catch (error) {
        if (error.name === 'AbortError') throw new Error('请求超时，请稍后重试');
        throw error;
    } finally {
        clearTimeout(timer);
    }
}

/* ------------------------- 具体接口 ------------------------- */

/** 榜单列表 */
export function fetchRepos(params) {
    return request('/repos', { params });
}

/** 项目详情（含 7 日趋势） */
export function fetchRepoDetail(repoId) {
    return request(`/repos/${repoId}`);
}

/** 语言列表 */
export function fetchLanguages() {
    return request('/languages');
}

/** 全局统计 */
export function fetchStats() {
    return request('/meta/stats');
}

/** 收藏 ID 集合 */
export function fetchFavoriteIds() {
    return request('/favorites/ids');
}

/** 新增收藏 */
export function addFavorite(repoId) {
    return request('/favorites', { method: 'POST', body: { repo_id: repoId } });
}

/** 取消收藏 */
export function removeFavorite(repoId) {
    return request(`/favorites/${repoId}`, { method: 'DELETE' });
}

/**
 * 手动触发数据抓取（一键刷新，无需输入 Token）。
 *
 * Admin Token 由后端从环境变量 ADMIN_TOKEN 读取；本机回环地址由 ADMIN_ALLOW_LOCAL 放行，
 * 公网部署请在服务端关闭 ADMIN_ALLOW_LOCAL 并通过 X-Admin-Token 调用。
 */
export function refreshData(force = true) {
    return request('/admin/refresh', { method: 'POST', body: { force } });
}

/**
 * Github 全网搜索（只读代理，不入库）。
 * 与本地库检索（fetchRepos）并行使用，结果在页面下方单独分区展示。
 */
export function searchGithub(keyword, perPage = 10) {
    return request('/search/github', { params: { keyword, per_page: perPage } });
}
