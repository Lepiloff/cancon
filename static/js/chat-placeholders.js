/**
 * Shared placeholder rotation for AI Budtender chat inputs.
 *
 * Reads localized placeholder strings from `window.ChatPlaceholders`,
 * which is populated by base_v2.html via Django {% trans %} tags.
 *
 * Public API:
 *   ChatPlaceholderRotator.attach(inputElement, options)
 *     Starts rotating the input's placeholder every `intervalMs` (default 5000)
 *     while the input is empty. Returns a `stop()` function for cleanup.
 */
(function() {
    var DEFAULT_INTERVAL_MS = 5000;

    function getPageLanguage() {
        var lang = document.documentElement.lang || 'es';
        return lang.split('-')[0].toLowerCase();
    }

    function getPlaceholders() {
        var pool = window.ChatPlaceholders || {};
        var lang = getPageLanguage();
        return pool[lang] || pool.es || [];
    }

    function getRandomPlaceholder() {
        var list = getPlaceholders();
        if (!list.length) return '';
        return list[Math.floor(Math.random() * list.length)];
    }

    function attach(input, options) {
        if (!input) return function noop() {};

        var intervalMs = (options && options.intervalMs) || DEFAULT_INTERVAL_MS;
        var isActive = (options && typeof options.isActive === 'function')
            ? options.isActive
            : function() { return true; };

        function update() {
            if (!input.value.trim() && isActive()) {
                var placeholder = getRandomPlaceholder();
                if (placeholder) input.placeholder = placeholder;
            }
        }

        // Set initial placeholder immediately
        update();

        var intervalId = setInterval(update, intervalMs);

        function stop() {
            clearInterval(intervalId);
        }

        // Auto-cleanup on page unload to avoid leaks on SPA-style navigation
        window.addEventListener('pagehide', stop, { once: true });

        return stop;
    }

    window.ChatPlaceholderRotator = {
        attach: attach,
        getRandomPlaceholder: getRandomPlaceholder
    };
})();
