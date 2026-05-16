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
                // Icon auch beim Init setzen
                const icon = document.getElementById('sidebar-toggle-icon');
                if (icon) {
                    icon.className = 'bi bi-arrow-bar-right';
                }
            }
        }

        // Theme Icon aktualisieren
        updateThemeIcon();

        // Tooltips initialisieren
        updateTooltips();
    }

    window.toggleSidebar = function() {
        const sidebar = document.getElementById('friday-sidebar');
        if (!sidebar) return;

        sidebar.classList.toggle('collapsed');
        const collapsed = sidebar.classList.contains('collapsed');
        const state = collapsed ? 'collapsed' : 'expanded';
        localStorage.setItem(SIDEBAR_KEY, state);

        // Icon wechseln
        const icon = document.getElementById('sidebar-toggle-icon');
        if (icon) {
            icon.className = collapsed
                ? 'bi bi-arrow-bar-right'
                : 'bi bi-arrow-bar-left';
        }

        // Tooltips aktualisieren
        updateTooltips();
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

    // Tooltip Management für collapsed State
    function updateTooltips() {
        const sidebar = document.getElementById('friday-sidebar');
        if (!sidebar) return;

        const collapsed = sidebar.classList.contains('collapsed');

        document.querySelectorAll('.sidebar-link[data-bs-title]').forEach(el => {
            const existing = bootstrap.Tooltip.getInstance(el);
            if (collapsed) {
                if (!existing) {
                    new bootstrap.Tooltip(el);
                }
            } else {
                if (existing) {
                    existing.dispose();
                }
            }
        });
    }

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

    // ── EasyMDE — Robuste Initialisierung ────────────────────────
    //
    // Problem: HTMX-Events feuern bevor das Element vollständig
    // gerendert ist → EasyMDE schlägt still fehl (offsetHeight = 0)
    //
    // Lösung: MutationObserver der jede neue textarea.md-editor erkennt
    // + requestAnimationFrame + setTimeout(0) für garantiertes Rendering

    const _mdInstances = new WeakMap(); // Editor-Instanzen merken

    function initEasyMDE(textarea) {
        // Bereits initialisiert?
        if (_mdInstances.has(textarea)) return;
        // Sicherheitscheck: Element muss sichtbar sein
        if (!textarea.isConnected) return;

        // requestAnimationFrame: nach dem nächsten Paint
        requestAnimationFrame(() => {
            // setTimeout(0): nach dem aktuellen Call-Stack (Layout abgeschlossen)
            setTimeout(() => {
                // Nochmals prüfen — könnte zwischenzeitlich entfernt worden sein
                if (!textarea.isConnected || _mdInstances.has(textarea)) return;

                // Check if EasyMDE is available
                if (typeof EasyMDE === 'undefined') {
                    console.warn('EasyMDE library not loaded for element:', textarea);
                    return;
                }

                try {
                    const editor = new EasyMDE({
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
                        status:           false,
                        minHeight:        '120px',
                        renderingConfig:  { singleLineBreaks: false },
                    });

                    _mdInstances.set(textarea, editor);

                    // Dark Mode sync
                    const theme = localStorage.getItem('friday-theme') || 'light';
                    if (theme === 'dark') {
                        editor.codemirror.getWrapperElement()
                            .classList.add('cm-s-dark');
                    }

                    // Theme-Change Event hören
                    document.addEventListener('friday:theme-changed', (e) => {
                        const wrapper = editor.codemirror.getWrapperElement();
                        wrapper.classList.toggle('cm-s-dark', e.detail.theme === 'dark');
                    });

                } catch (err) {
                    // EasyMDE Fehler loggen aber nicht crashen
                    console.warn('EasyMDE init failed for element:', textarea, err);
                }
            }, 0);
        });
    }

    // MutationObserver — überwacht das gesamte DOM auf neue md-editor Elemente
    const _mdObserver = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType !== Node.ELEMENT_NODE) continue;

                // Direkt eine textarea.md-editor?
                if (node.matches?.('textarea.md-editor')) {
                    initEasyMDE(node);
                }

                // Oder enthält textarea.md-editor als Kind?
                node.querySelectorAll?.('textarea.md-editor').forEach(initEasyMDE);
            }
        }
    });

    // Observer starten — gesamtes Document überwachen
    _mdObserver.observe(document.body, {
        childList: true,
        subtree:   true,
    });

    // Bereits im DOM vorhandene Editoren initialisieren (Seiten-Load)
    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('textarea.md-editor').forEach(initEasyMDE);
    });

    // Nach dem Öffnen des Slide-Overs — EasyMDE neu initialisieren
    // wenn der Container vorher versteckt war
    function onSlideoverOpen() {
        const slideover = document.getElementById('slide-over');
        if (!slideover) return;

        // Kurz warten bis der Container sichtbar ist
        requestAnimationFrame(() => {
            setTimeout(() => {
                slideover.querySelectorAll('textarea.md-editor').forEach(textarea => {
                    // Bestehende Instanz entfernen und neu initialisieren
                    if (_mdInstances.has(textarea)) {
                        const old = _mdInstances.get(textarea);
                        try { old.toTextArea(); } catch(e) {}
                        _mdInstances.delete(textarea);
                    }
                    initEasyMDE(textarea);
                });
            }, 50); // 50ms: genug Zeit für CSS-Transition
        });
    }

    // HTMX Event: nach Slide-Over Swap
    document.addEventListener('htmx:afterSettle', (e) => {
        const target = e.detail.target;
        if (target?.id === 'slide-over') {
            onSlideoverOpen();
        }
    });

    // Bootstrap Modal shown Event — Editor initialisieren
    document.addEventListener('shown.bs.modal', (e) => {
        e.target.querySelectorAll('textarea.md-editor').forEach(textarea => {
            if (_mdInstances.has(textarea)) {
                const old = _mdInstances.get(textarea);
                try { old.toTextArea(); } catch(e) {}
                _mdInstances.delete(textarea);
            }
            initEasyMDE(textarea);
        });
    });

    // Aufräumen bei HTMX beforeSwap — Memory Leak vermeiden
    document.addEventListener('htmx:beforeSwap', (e) => {
        const target = e.detail.target;
        if (!target) return;
        target.querySelectorAll('textarea.md-editor').forEach(textarea => {
            if (_mdInstances.has(textarea)) {
                const instance = _mdInstances.get(textarea);
                try { instance.toTextArea(); } catch(err) {}
                _mdInstances.delete(textarea);
            }
        });
    });


    // ── Markdown Rendering (marked.js + DOMPurify) ────────────────
    // Wird auf alle <div class="md-render"> angewendet
    // data-md Attribut enthält den Markdown-Text (oder Inhalt des divs)

    function renderMarkdown(container) {
        const target = container || document;
        target.querySelectorAll('.md-render').forEach(el => {
            let raw = el.dataset.md || el.textContent || '';

            // Doppelt-escaped Unicode-Escapes auflösen
            // \\u000A → \n, \\u002D → -, \\u002A → * etc.
            try {
                raw = raw.replace(
                    /\\u([0-9A-Fa-f]{4})/g,
                    (_, code) => String.fromCharCode(parseInt(code, 16))
                );
            } catch(e) {}

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


    // ── @Mentions mit Tribute.js ──────────────────────────────────

    function initMentions(container) {
        const target = container || document;

        target.querySelectorAll('textarea.mention-enabled').forEach(textarea => {
            // Skip if already initialized
            if (textarea.dataset.tributeInitialized) return;
            textarea.dataset.tributeInitialized = 'true';

            const tribute = new Tribute({
                trigger: '@',
                allowSpaces: false,
                menuItemLimit: 8,

                // Load users from server
                values: function(text, callback) {
                    fetch(`/accounts/api/users/search/?q=${encodeURIComponent(text)}`)
                        .then(r => r.json())
                        .then(data => callback(data.users))
                        .catch(() => callback([]));
                },

                // Render dropdown item
                menuItemTemplate: (item) => `
                    <div class="d-flex align-items-center gap-2">
                        <div style="width:24px; height:24px; border-radius:50%;
                                    background:#2d6a4f; color:#fff; font-size:10px;
                                    display:flex; align-items:center; justify-content:center;
                                    font-weight:600; flex-shrink:0;">
                            ${item.original.initials}
                        </div>
                        <div>
                            <div style="font-size:13px; font-weight:500;">${item.original.value}</div>
                            <div style="font-size:11px; opacity:.6;">@${item.original.key}</div>
                        </div>
                    </div>
                `,

                // What gets inserted into text
                selectTemplate: (item) => `@${item.original.key}`,

                // Lookup field
                lookup: 'value',
                fillAttr: 'key',
            });

            tribute.attach(textarea);
        });
    }

    // Initialize mentions on page load
    initMentions();

    // Re-initialize after HTMX swaps (slide-over, etc.)
    document.addEventListener('htmx:afterSettle', (e) => initMentions(e.detail.target));

    // ── Task Tab Badge Counter Updates (ISSUE-66) ────────────────────

    // Update tab badge counters after HTMX updates
    document.addEventListener('htmx:afterSettle', (e) => {
        // Update Subtasks badge
        const subtaskItems = document.querySelectorAll('#tab-subtasks .subtask-item, #tab-subtasks-so .subtask-item');
        const subtaskCount = subtaskItems.length;
        const subtaskBadges = document.querySelectorAll('[data-bs-target="#tab-subtasks"] .badge, [data-bs-target="#tab-subtasks-so"] .badge');
        subtaskBadges.forEach(badge => {
            if (subtaskCount > 0) {
                badge.textContent = subtaskCount;
                badge.style.display = '';
            } else {
                badge.style.display = 'none';
            }
        });

        // Update Attachments badge
        const attachmentItems = document.querySelectorAll('#tab-attachments .attachment-item, #tab-attachments-so .attachment-item');
        const attachmentCount = attachmentItems.length;
        const attachmentBadges = document.querySelectorAll('[data-bs-target="#tab-attachments"] .badge, [data-bs-target="#tab-attachments-so"] .badge');
        attachmentBadges.forEach(badge => {
            if (attachmentCount > 0) {
                badge.textContent = attachmentCount;
                badge.style.display = '';
            } else {
                badge.style.display = 'none';
            }
        });

        // Update Time Entries badge
        const timeEntryItems = document.querySelectorAll('#tab-time .time-entry-item, #tab-time-so .time-entry-item');
        const timeEntryCount = timeEntryItems.length;
        const timeEntryBadges = document.querySelectorAll('[data-bs-target="#tab-time"] .badge, [data-bs-target="#tab-time-so"] .badge');
        timeEntryBadges.forEach(badge => {
            if (timeEntryCount > 0) {
                badge.textContent = timeEntryCount;
                badge.style.display = '';
            } else {
                badge.style.display = 'none';
            }
        });

        // Update Dependencies badge
        const dependencyItems = document.querySelectorAll('#tab-dependencies .dependency-item, #tab-dependencies-so .dependency-item');
        const dependencyCount = dependencyItems.length;
        const dependencyBadges = document.querySelectorAll('[data-bs-target="#tab-dependencies"] .badge, [data-bs-target="#tab-dependencies-so"] .badge');
        dependencyBadges.forEach(badge => {
            if (dependencyCount > 0) {
                badge.textContent = dependencyCount;
                badge.style.display = '';
            } else {
                badge.style.display = 'none';
            }
        });
    });

    // ── Task Actions (ISSUE-53) ──────────────────────────────────────

    // Task Closed Event Handler
    document.addEventListener('taskClosed', () => {
        // Close modal
        const modalEl = document.getElementById('task-close-modal-container');
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal?.hide();
        }

        // Reload Slide-Over if open
        const slideOver = document.getElementById('slide-over');
        if (slideOver && slideOver.dataset.taskId) {
            htmx.ajax('GET',
                `/tasks/${slideOver.dataset.taskId}/detail/`,
                { target: '#slide-over', swap: 'innerHTML' }
            );
        }

        // Refresh Kanban Board if visible
        const kanbanBoard = document.getElementById('kanban-board');
        if (kanbanBoard) {
            htmx.trigger(kanbanBoard, 'refresh');
        }

        // Reload full page if we're on task detail full view
        if (window.location.pathname.match(/^\/tasks\/\d+\/$/)) {
            window.location.reload();
        }
    });

    // Task Assigned Event Handler
    document.addEventListener('taskAssigned', () => {
        // Close modal
        const modalEl = document.getElementById('task-assign-modal-container');
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal?.hide();
        }

        // Reload Slide-Over if open
        const slideOver = document.getElementById('slide-over');
        if (slideOver && slideOver.dataset.taskId) {
            htmx.ajax('GET',
                `/tasks/${slideOver.dataset.taskId}/detail/`,
                { target: '#slide-over', swap: 'innerHTML' }
            );
        }

        // Refresh Kanban Board if visible
        const kanbanBoard = document.getElementById('kanban-board');
        if (kanbanBoard) {
            htmx.trigger(kanbanBoard, 'refresh');
        }
    });

    // Task Moved Event Handler
    document.addEventListener('taskMoved', () => {
        // Close modal
        const modalEl = document.getElementById('task-move-modal-container');
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal?.hide();
        }

        // Refresh Kanban Board if visible
        const kanbanBoard = document.getElementById('kanban-board');
        if (kanbanBoard) {
            htmx.trigger(kanbanBoard, 'refresh');
        }

        // Close Slide-Over (task is now in another project)
        closeSlideOver();
    });

})();
