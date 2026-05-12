/**
 * Friday JavaScript
 * Theme toggle and HTMX helpers
 */

(function() {
    'use strict';

    // Theme Toggle Functionality
    const themeToggle = document.getElementById('theme-toggle');
    const themeIconLight = document.getElementById('theme-icon-light');
    const themeIconDark = document.getElementById('theme-icon-dark');

    // Get current theme from localStorage or default to light
    function getCurrentTheme() {
        return localStorage.getItem('friday-theme') || 'light';
    }

    // Set theme
    function setTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem('friday-theme', theme);
        updateThemeIcon(theme);
    }

    // Update theme toggle icon
    function updateThemeIcon(theme) {
        if (!themeIconLight || !themeIconDark) return;

        if (theme === 'dark') {
            themeIconLight.classList.add('d-none');
            themeIconDark.classList.remove('d-none');
        } else {
            themeIconLight.classList.remove('d-none');
            themeIconDark.classList.add('d-none');
        }
    }

    // Toggle theme
    function toggleTheme() {
        const currentTheme = getCurrentTheme();
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
    }

    // Initialize theme on page load
    function initTheme() {
        const theme = getCurrentTheme();
        updateThemeIcon(theme);
    }

    // Event listeners
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }

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

})();
