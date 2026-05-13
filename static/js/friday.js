/**
 * Friday JavaScript
 * Theme toggle and HTMX helpers
 */

(function() {
    'use strict';

    // ── Sidebar State ─────────────────────────────────────────────

    const SIDEBAR_KEY = 'friday-sidebar';

    function initSidebar() {
        const sidebar = document.getElementById('friday-sidebar');
        if (!sidebar) return;

        // Gespeicherten State laden (nur Desktop)
        if (window.innerWidth > 992) {
            const saved = localStorage.getItem(SIDEBAR_KEY) || 'expanded';
            if (saved === 'collapsed') {
                sidebar.classList.add('collapsed');
            }
        }

        // Theme Icon aktualisieren
        updateThemeIcon();
    }

    window.toggleSidebar = function() {
        const sidebar = document.getElementById('friday-sidebar');
        if (!sidebar) return;

        sidebar.classList.toggle('collapsed');
        const state = sidebar.classList.contains('collapsed') ? 'collapsed' : 'expanded';
        localStorage.setItem(SIDEBAR_KEY, state);
    };

    window.openSidebarMobile = function() {
        const sidebar  = document.getElementById('friday-sidebar');
        const backdrop = document.getElementById('sidebar-backdrop');
        sidebar?.classList.add('mobile-open');
        backdrop?.classList.add('active');
        document.body.style.overflow = 'hidden';
    };

    window.closeSidebarMobile = function() {
        const sidebar  = document.getElementById('friday-sidebar');
        const backdrop = document.getElementById('sidebar-backdrop');
        sidebar?.classList.remove('mobile-open');
        backdrop?.classList.remove('active');
        document.body.style.overflow = '';
    };

    // Schließen bei Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') window.closeSidebarMobile();
    });

    // Schließen bei Resize auf Desktop
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) window.closeSidebarMobile();
    });

    // Init beim Laden
    document.addEventListener('DOMContentLoaded', initSidebar);


    // ── Theme Toggle ──────────────────────────────────────────────

    // Update theme toggle icon
    function updateThemeIcon() {
        const theme = localStorage.getItem('friday-theme') || 'light';
        const icon  = document.getElementById('theme-icon');
        if (!icon) return;
        icon.className = theme === 'dark'
            ? 'bi bi-sun'
            : 'bi bi-moon-stars';
    }

    // Toggle theme
    window.toggleTheme = function() {
        const html    = document.documentElement;
        const current = html.getAttribute('data-bs-theme') || 'light';
        const next    = current === 'light' ? 'dark' : 'light';
        html.setAttribute('data-bs-theme', next);
        localStorage.setItem('friday-theme', next);
        updateThemeIcon();
        // EasyMDE Editoren informieren
        document.dispatchEvent(new CustomEvent('friday:theme-changed',
            { detail: { theme: next } }));
    };


    // HTMX Event Handlers
    document.addEventListener('htmx:afterSwap', function(event) {
        // Re-initialize any Bootstrap components after HTMX swap
        const tooltips = event.detail.target.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(function(tooltip) {
            new bootstrap.Tooltip(tooltip);
        });

        // Show slide-over and backdrop if content was loaded
        if (event.detail.target.id === 'slide-over' && event.detail.target.innerHTML.trim()) {
            event.detail.target.classList.add('active');
            const backdrop = document.getElementById('slide-over-backdrop');
            if (backdrop) {
                backdrop.classList.add('active');
            }
        }
    });

    // Slide-over close function
    window.closeSlideOver = function() {
        const slideOver = document.getElementById('slide-over');
        const backdrop = document.getElementById('slide-over-backdrop');

        if (slideOver) {
            slideOver.classList.remove('active');
            // Wait for animation to complete before clearing content
            setTimeout(function() {
                slideOver.innerHTML = '';
            }, 300);
        }

        if (backdrop) {
            backdrop.classList.remove('active');
        }

        // If URL was pushed, go back in history
        if (window.location.pathname.includes('/tasks/') && window.location.pathname.includes('/detail/')) {
            window.history.back();
        }
    };

    // Handle browser back button to close slide-over
    window.addEventListener('popstate', function(event) {
        if (!window.location.pathname.includes('/tasks/') || !window.location.pathname.includes('/detail/')) {
            const slideOver = document.getElementById('slide-over');
            const backdrop = document.getElementById('slide-over-backdrop');

            if (slideOver && slideOver.innerHTML.trim() !== '') {
                slideOver.classList.remove('active');
                setTimeout(function() {
                    slideOver.innerHTML = '';
                }, 300);
            }

            if (backdrop) {
                backdrop.classList.remove('active');
            }
        }
    });

    // ── Markdown Editor (EasyMDE) ─────────────────────────────────
    // Wird automatisch auf alle <textarea class="md-editor"> angewendet
    // HTMX-aware: neu initialisieren nach HTMX Swap

    function initMarkdownEditors(container) {
        const target = container || document;
        target.querySelectorAll('textarea.md-editor').forEach(textarea => {
            // Bereits initialisiert? Überspringen
            if (textarea.dataset.mdInitialized) return;
            textarea.dataset.mdInitialized = 'true';

            // Check if EasyMDE is available
            if (typeof EasyMDE === 'undefined') {
                console.error('EasyMDE library not loaded');
                // Fallback: show a visible warning
                const warning = document.createElement('div');
                warning.className = 'alert alert-warning';
                warning.textContent = 'Markdown editor library not loaded. Please refresh the page.';
                textarea.parentNode.insertBefore(warning, textarea);
                return;
            }

            const easyMDE = new EasyMDE({
                element:          textarea,
                spellChecker:     false,
                autosave:         { enabled: false },
                toolbar: [
                    'bold', 'italic', 'heading', '|',
                    'unordered-list', 'ordered-list', '|',
                    'link', 'quote', 'code', '|',
                    'preview', 'side-by-side', '|',
                    'guide',
                ],
                placeholder:      'Beschreibung eingeben... (Markdown wird unterstützt)',
                status:           false,          // Statusleiste ausblenden
                minHeight:        '120px',
                renderingConfig: {
                    singleLineBreaks: false,
                    codeSyntaxHighlighting: false,
                },
                // Theming: passt sich an Light/Dark Mode an
                theme:            document.documentElement.getAttribute('data-bs-theme') === 'dark'
                                  ? 'dark' : 'default',
            });

            // Dark Mode Toggle: Editor-Theme aktualisieren
            document.addEventListener('friday:theme-changed', (e) => {
                const wrapper = easyMDE.codemirror.getWrapperElement();
                wrapper.classList.toggle('cm-s-dark', e.detail.theme === 'dark');
            });
        });
    }

    // Initial + nach jedem HTMX Swap
    initMarkdownEditors();
    document.addEventListener('htmx:afterSwap', (e) => initMarkdownEditors(e.detail.target));
    document.addEventListener('htmx:afterSettle', (e) => initMarkdownEditors(e.detail.target));


    // ── Markdown Rendering (marked.js + DOMPurify) ────────────────
    // Wird auf alle <div class="md-render"> angewendet
    // data-md Attribut enthält den Markdown-Text (oder Inhalt des divs)

    function renderMarkdown(container) {
        const target = container || document;
        target.querySelectorAll('.md-render').forEach(el => {
            const raw = el.dataset.md || el.textContent || '';
            if (!raw.trim()) {
                el.innerHTML = '<span class="text-muted fst-italic">Keine Beschreibung</span>';
                return;
            }
            // Support both marked v4+ (marked.parse) and older versions (marked())
            let markdownHtml;
            if (typeof marked.parse === 'function') {
                markdownHtml = marked.parse(raw);
            } else if (typeof marked === 'function') {
                markdownHtml = marked(raw);
            } else {
                console.error('marked.js library not loaded');
                el.innerHTML = '<span class="text-danger">Error: Markdown library not loaded</span>';
                return;
            }

            const html = DOMPurify.sanitize(markdownHtml, {
                ALLOWED_TAGS: [
                    'h1','h2','h3','h4','h5','h6',
                    'p','br','hr',
                    'strong','em','del','code','pre',
                    'ul','ol','li',
                    'blockquote',
                    'a','img',
                    'table','thead','tbody','tr','th','td',
                ],
                ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'target', 'class'],
            });
            el.innerHTML = html;
            // Links in neuem Tab öffnen
            el.querySelectorAll('a').forEach(a => {
                a.setAttribute('target', '_blank');
                a.setAttribute('rel', 'noopener noreferrer');
            });
        });
    }

    renderMarkdown();
    document.addEventListener('htmx:afterSwap', (e) => renderMarkdown(e.detail.target));
    document.addEventListener('htmx:afterSettle', (e) => renderMarkdown(e.detail.target));

})();
