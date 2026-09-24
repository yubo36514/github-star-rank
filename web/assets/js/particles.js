/**
 * 页面背景：自绘 Canvas 星点漂移（零依赖，替代原 particles.js 粒子库）。
 *
 * 设计要点：
 * - 深色渐变打底（见 main.css 的 .particles-layer），上层绘制半透明星点缓慢斜向上漂移
 * - 星点不连线、不响应鼠标，避免干扰文字与卡片阅读
 * - DPR 上限 2、星点数量按可视面积计算并封顶（≤120），控制重绘成本
 * - 页面切到后台自动暂停；尊重系统「减少动效」偏好，降级为静态渐变且不创建 canvas
 */

/** 星点配色（沿用页面主色，保证深色主题统一） */
const STAR_COLORS = ['#58a6ff', '#a371f7', '#c9d1d9'];

/** 星点数量上限 */
const MAX_STARS = 120;

/** 每颗星点分摊的可视面积（px²），用于按屏幕大小计算数量 */
const AREA_PER_STAR = 22000;

/** 速度范围（px / 秒），刻意取极小值以保持「低干扰」 */
const SPEED_X = [-4, 4];
const SPEED_Y = [-8, -2];

/** 初始化背景（导出名保持不变，app.js 无需改动） */
export function initParticles() {
    const container = document.getElementById('particles-js');
    if (!container) return;

    // 系统开启「减少动效」时只保留静态渐变，不创建 canvas
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        container.classList.add('is-static');
        return;
    }

    const canvas = document.createElement('canvas');
    canvas.className = 'particles-canvas';
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        // 极少数环境拿不到 2d 上下文，降级为静态渐变
        container.classList.add('is-static');
        return;
    }
    container.appendChild(canvas);

    let width = 0;
    let height = 0;
    let stars = [];
    let rafId = null;
    let lastTs = 0;
    let resizeTimer = null;

    /** 区间随机 */
    const rand = (min, max) => min + Math.random() * (max - min);

    /** 生成星点：位置、半径、颜色、明暗相位与漂移速度 */
    function buildStars() {
        const count = Math.min(
            MAX_STARS,
            Math.max(30, Math.round((width * height) / AREA_PER_STAR))
        );
        stars = Array.from({ length: count }, () => ({
            x: Math.random() * width,
            y: Math.random() * height,
            r: rand(0.6, 1.7),
            color: STAR_COLORS[Math.floor(Math.random() * STAR_COLORS.length)],
            baseAlpha: rand(0.15, 0.5),
            // 明暗呼吸：每颗星点有独立频率与相位
            twinkle: rand(0.0006, 0.0022),
            phase: Math.random() * Math.PI * 2,
            vx: rand(SPEED_X[0], SPEED_X[1]),
            vy: rand(SPEED_Y[0], SPEED_Y[1]),
        }));
    }

    /** 同步画布尺寸（DPR 上限 2，避免高分屏下重绘成本过高） */
    function resize() {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        width = container.clientWidth || window.innerWidth;
        height = container.clientHeight || window.innerHeight;
        canvas.width = Math.floor(width * dpr);
        canvas.height = Math.floor(height * dpr);
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        buildStars();
    }

    /** 绘制一帧 */
    function draw(ts) {
        // 限制单帧步长：从后台切回时不会跳变
        const dt = lastTs ? Math.min(ts - lastTs, 50) : 16;
        lastTs = ts;
        const step = dt / 1000;

        ctx.clearRect(0, 0, width, height);
        for (let i = 0; i < stars.length; i += 1) {
            const star = stars[i];
            star.x += star.vx * step;
            star.y += star.vy * step;

            // 出界后从对侧回绕，保持画面始终有星点
            if (star.y < -4) {
                star.y = height + 4;
                star.x = Math.random() * width;
            } else if (star.y > height + 4) {
                star.y = -4;
            }
            if (star.x < -4) {
                star.x = width + 4;
            } else if (star.x > width + 4) {
                star.x = -4;
            }

            const alpha = star.baseAlpha + Math.sin(ts * star.twinkle + star.phase) * 0.16;
            ctx.globalAlpha = Math.max(0.06, Math.min(0.62, alpha));
            ctx.fillStyle = star.color;
            ctx.beginPath();
            ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.globalAlpha = 1;
    }

    function frame(ts) {
        draw(ts);
        rafId = requestAnimationFrame(frame);
    }

    function start() {
        if (rafId === null) {
            lastTs = 0;
            rafId = requestAnimationFrame(frame);
        }
    }

    function stop() {
        if (rafId !== null) {
            cancelAnimationFrame(rafId);
            rafId = null;
        }
    }

    // 窗口尺寸变化：节流重建，避免频繁重排
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(resize, 150);
    });

    // 页面切到后台时停止绘制，节省 CPU
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) stop();
        else start();
    });

    resize();
    start();
}
