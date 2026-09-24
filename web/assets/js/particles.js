/**
 * 页面背景粒子特效。
 * 使用 particles.js（本地 vendor/particles.min.js，离线可用）：
 * - 粒子漂浮 + 邻近连线
 * - 鼠标悬停产生抓取连线，点击时新增粒子
 * - 移动端自动减少粒子数量
 * - 尊重系统「减少动效」偏好；页面不可见时暂停渲染
 */

/** 初始化粒子背景 */
export function initParticles() {
    const container = document.getElementById('particles-js');
    if (!container || typeof window.particlesJS !== 'function') {
        console.warn('[particles] 粒子库未加载，已降级为静态渐变背景');
        return;
    }

    // 系统开启「减少动效」时不做粒子动画
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion) {
        container.style.background = 'radial-gradient(1200px 600px at 20% -10%, #12243d 0%, transparent 60%), var(--bg)';
        return;
    }

    const isMobile = window.innerWidth < 720;
    const particleCount = isMobile ? 40 : 90;

    window.particlesJS('particles-js', {
        particles: {
            number: { value: particleCount, density: { enable: true, value_area: 900 } },
            color: { value: ['#58a6ff', '#a371f7', '#3fb950'] },
            shape: { type: 'circle' },
            opacity: { value: 0.45, random: true, anim: { enable: true, speed: 0.4, opacity_min: 0.1 } },
            size: { value: 3, random: true },
            line_linked: {
                enable: true,
                distance: 140,
                color: '#58a6ff',
                opacity: 0.18,
                width: 1,
            },
            move: {
                enable: true,
                speed: 1.1,
                direction: 'none',
                random: true,
                out_mode: 'out',
                bounce: false,
            },
        },
        interactivity: {
            detect_on: 'window',
            events: {
                onhover: { enable: true, mode: 'grab' },
                onclick: { enable: true, mode: 'push' },
                resize: true,
            },
            modes: {
                grab: { distance: 160, line_linked: { opacity: 0.5 } },
                push: { particles_nb: 3 },
            },
        },
        retina_detect: true,
    });

    // 页面切到后台时暂停动画，回到前台再恢复，节省 CPU
    document.addEventListener('visibilitychange', () => {
        const canvas = container.querySelector('canvas');
        if (!canvas) return;
        canvas.style.display = document.hidden ? 'none' : 'block';
    });
}
