/**
 * 前端全局配置。
 * 前后端分离：页面通过 RESTful 接口获取数据；默认与页面同源，
 * 若需要把前端部署到别的域名，可在 index.html 中设置 window.__API_BASE__。
 */

/** 接口基址，例如 "http://localhost:8000"，同源部署时为空字符串 */
export const API_BASE = (window.__API_BASE__ || '').replace(/\/+$/, '');

/** 接口前缀 */
export const API_PREFIX = '/api/v1';

/** localStorage 中保存客户端标识的 key（用于收藏隔离，无需登录） */
export const CLIENT_ID_KEY = 'gh_rank_client_id';

/** 触发 Github 全网搜索的最小关键词长度（防止逐字符打满 Search API 配额） */
export const REMOTE_SEARCH_MIN_LEN = 2;

/** 搜索防抖时间（毫秒）：本地库 + 全网搜索共用 */
export const SEARCH_DEBOUNCE = 450;

/** localStorage 中保存筛选偏好的 key */
export const FILTER_STORE_KEY = 'gh_rank_filters';

/** 接口超时时间（毫秒） */
export const REQUEST_TIMEOUT = 20000;
