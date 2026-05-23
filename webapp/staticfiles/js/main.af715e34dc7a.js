/* ============================================================
   Guardian Agent – JavaScript v2
   Navbar, animations, counters, particles, interactive glows
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

    // ---- Navbar scroll effect ----
    const nav = document.getElementById('mainNav');
    if (nav) {
        const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 40);
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    // ---- Smooth scroll for anchor links ----
    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', e => {
            const target = document.querySelector(a.getAttribute('href'));
            if (target) {
                e.preventDefault();
                const y = target.getBoundingClientRect().top + window.pageYOffset - 80;
                window.scrollTo({ top: y, behavior: 'smooth' });
            }
        });
    });

    // ---- Scroll-triggered animations (staggered) ----
    const animateElements = document.querySelectorAll('[data-animate]');
    const observer = new IntersectionObserver(
        entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const delay = parseInt(entry.target.dataset.delay || '0', 10);
                    setTimeout(() => entry.target.classList.add('visible'), delay);
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.12 }
    );
    animateElements.forEach(el => observer.observe(el));

    // ---- Animated counters ----
    const counters = document.querySelectorAll('.counter');
    const counterObserver = new IntersectionObserver(
        entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    counterObserver.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.5 }
    );
    counters.forEach(c => counterObserver.observe(c));

    function animateCounter(el) {
        const target = parseInt(el.dataset.target, 10);
        const duration = 1800;
        const step = target / (duration / 16);
        let current = 0;
        const timer = setInterval(() => {
            current = Math.min(current + step, target);
            el.textContent = formatNum(Math.floor(current));
            if (current >= target) clearInterval(timer);
        }, 16);
    }

    function formatNum(n) {
        if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000)    return (n / 1000).toFixed(n % 1000 === 0 ? 0 : 1) + 'K';
        return n.toString();
    }

    // ---- Floating particles (hero) ----
    const particleContainer = document.getElementById('particles');
    if (particleContainer) {
        for (let i = 0; i < 18; i++) {
            const p = document.createElement('div');
            p.classList.add('particle');
            const size = Math.random() * 5 + 2;
            p.style.cssText = `
                width:${size}px;height:${size}px;
                left:${Math.random() * 100}%;
                top:${Math.random() * 100}%;
                animation-delay:${Math.random() * 6}s;
                animation-duration:${Math.random() * 6 + 6}s;
            `;
            particleContainer.appendChild(p);
        }
    }

    // ---- Interactive gradient bubble (cursor tracking) ----
    const interactiveBubbles = document.querySelectorAll('.interactive');
    if (interactiveBubbles.length > 0) {
        let curX = 0, curY = 0, tgX = 0, tgY = 0;
        window.addEventListener('mousemove', e => { tgX = e.clientX; tgY = e.clientY; });
        function moveGradient() {
            curX += (tgX - curX) / 20;
            curY += (tgY - curY) / 20;
            interactiveBubbles.forEach(b => {
                b.style.transform = `translate(${Math.round(curX)}px, ${Math.round(curY)}px)`;
            });
            requestAnimationFrame(moveGradient);
        }
        moveGradient();
    }

    // ---- Risk bar animation (dashboard) ----
    const riskBars = document.querySelectorAll('.risk-bar');
    if (riskBars.length > 0) {
        const barObserver = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const bar = entry.target;
                    const targetWidth = bar.style.width;
                    bar.style.width = '0%';
                    setTimeout(() => { bar.style.width = targetWidth; }, 100);
                    barObserver.unobserve(bar);
                }
            });
        }, { threshold: 0.2 });
        riskBars.forEach(b => barObserver.observe(b));
    }

    // ---- Card hover tilt effect ----
    document.querySelectorAll('.feature-card, .pricing-card, .install-card').forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width - 0.5;
            const y = (e.clientY - rect.top) / rect.height - 0.5;
            card.style.transform = `translateY(-5px) rotateX(${-y * 3}deg) rotateY(${x * 3}deg)`;
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });

    // ---- Footer link hover ----
    document.querySelectorAll('.footer-section a').forEach(a => {
        a.addEventListener('mouseenter', () => { a.style.color = 'rgba(255,255,255,0.75)'; });
        a.addEventListener('mouseleave', () => { a.style.color = ''; });
    });

});
