/* ═══════════════════════════════════════════════════════════════
   JMD Makeover Studio & Academy — JavaScript
   ═══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {

    // ── Navbar Scroll Effect ──────────────────────────────────
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // ── Mobile Nav Toggle ─────────────────────────────────────
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    const navAuth = document.querySelector('.nav-auth');

    if (navToggle) {
        navToggle.addEventListener('click', function () {
            navToggle.classList.toggle('active');
            if (navLinks) navLinks.classList.toggle('active');
            if (navAuth) navAuth.classList.toggle('active');
        });

        // Close on link click
        document.querySelectorAll('.nav-links a').forEach(function (link) {
            link.addEventListener('click', function () {
                navToggle.classList.remove('active');
                if (navLinks) navLinks.classList.remove('active');
                if (navAuth) navAuth.classList.remove('active');
            });
        });
    }

    // ── Flash Message Auto-dismiss ────────────────────────────
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function (msg, index) {
        // Click to dismiss
        msg.addEventListener('click', function () {
            msg.style.animation = 'slideOutRight 0.3s ease forwards';
            setTimeout(function () { msg.remove(); }, 300);
        });

        // Auto dismiss after 5s
        setTimeout(function () {
            if (msg.parentNode) {
                msg.style.animation = 'slideOutRight 0.3s ease forwards';
                setTimeout(function () { msg.remove(); }, 300);
            }
        }, 5000 + index * 500);
    });

    // ── Admin Sidebar Toggle (Mobile) ─────────────────────────
    const sidebarToggle = document.querySelector('.admin-sidebar-toggle');
    const sidebar = document.querySelector('.admin-sidebar');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('active');
        });

        // Close sidebar on outside click
        document.addEventListener('click', function (e) {
            if (sidebar.classList.contains('active') &&
                !sidebar.contains(e.target) &&
                !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        });
    }

    // ── Date Picker Min Date ──────────────────────────────────
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function (input) {
        if (input.dataset.minToday === 'true' || input.hasAttribute('min')) {
            if (!input.getAttribute('min')) {
                const today = new Date().toISOString().split('T')[0];
                input.setAttribute('min', today);
            }
        }
    });

    // ── Image Preview on Upload ───────────────────────────────
    const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    imageInputs.forEach(function (input) {
        input.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (!file) return;

            const preview = input.parentElement.querySelector('.image-preview');
            if (preview) {
                const reader = new FileReader();
                reader.onload = function (ev) {
                    preview.innerHTML = '<img src="' + ev.target.result + '" style="max-width:200px;max-height:150px;border-radius:8px;margin-top:8px;">';
                };
                reader.readAsDataURL(file);
            }
        });
    });

    // ── Gallery Lightbox ──────────────────────────────────────
    const galleryItems = document.querySelectorAll('.gallery-item');
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightbox-img');

    galleryItems.forEach(function (item) {
        item.addEventListener('click', function () {
            const img = item.querySelector('img');
            if (img && lightbox && lightboxImg) {
                lightboxImg.src = img.src;
                lightbox.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        });
    });

    if (lightbox) {
        lightbox.addEventListener('click', function (e) {
            if (e.target === lightbox || e.target.classList.contains('lightbox-close')) {
                lightbox.classList.remove('active');
                document.body.style.overflow = '';
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && lightbox.classList.contains('active')) {
                lightbox.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }

    // ── Modal Management ──────────────────────────────────────
    // Open modal
    document.querySelectorAll('[data-modal]').forEach(function (trigger) {
        trigger.addEventListener('click', function (e) {
            e.preventDefault();
            const modalId = trigger.dataset.modal;
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        });
    });

    // Close modal
    document.querySelectorAll('.modal-close, .modal-cancel').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const modal = btn.closest('.modal-backdrop');
            if (modal) {
                modal.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });

    // Close on backdrop click
    document.querySelectorAll('.modal-backdrop').forEach(function (backdrop) {
        backdrop.addEventListener('click', function (e) {
            if (e.target === backdrop) {
                backdrop.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });

    // ── Confirm Delete ────────────────────────────────────────
    document.querySelectorAll('.btn-delete-confirm').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });

    // ── Scroll Animations ─────────────────────────────────────
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.style.animation = 'fadeInUp 0.6s ease forwards';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.card, .stat-card, .admin-stat-card, .contact-item').forEach(function (el) {
        el.style.opacity = '0';
        observer.observe(el);
    });

    // ── Smooth scroll for anchor links ────────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
});

// Add slideOutRight animation
const style = document.createElement('style');
style.textContent = '@keyframes slideOutRight { to { opacity: 0; transform: translateX(40px); } }';
document.head.appendChild(style);
