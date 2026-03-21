/**
 * Cookie Consent Banner
 *
 * Reads config from window.CookieConsentConfig (set by Django template).
 * Posts consent choice to /cookie-consent/ to persist user preference.
 * GA4 is loaded unconditionally via the template.
 */
(function () {
    'use strict';

    /* ------------------------------------------------------------------
       POST consent to server
       ------------------------------------------------------------------ */

    function postConsent(analytics) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/cookie-consent/', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(JSON.stringify({ analytics: analytics }));
    }

    /* ------------------------------------------------------------------
       Banner show / hide
       ------------------------------------------------------------------ */

    function showBanner(banner) {
        requestAnimationFrame(function () {
            banner.classList.add('cookie-consent--visible');
            var firstBtn = banner.querySelector('.cookie-consent__btn--accept');
            if (firstBtn) firstBtn.focus({ preventScroll: true });
        });
    }

    function hideBanner(banner) {
        banner.classList.add('cookie-consent--hiding');
        banner.classList.remove('cookie-consent--visible');

        var onEnd = function () {
            banner.removeEventListener('transitionend', onEnd);
            banner.remove();
        };

        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            banner.remove();
        } else {
            banner.addEventListener('transitionend', onEnd);
            setTimeout(function () { try { banner.remove(); } catch (_) {} }, 800);
        }
    }

    /* ------------------------------------------------------------------
       Init
       ------------------------------------------------------------------ */

    function init() {
        var cfg = window.CookieConsentConfig || {};

        // Restore cookie for authenticated user (no banner needed)
        if (cfg.restoreConsent) {
            var consent = cfg.consent || {};
            postConsent(!!consent.analytics);
            return;
        }

        if (!cfg.showBanner) return;

        var banner = document.getElementById('cookie-consent-banner');
        if (!banner) return;

        showBanner(banner);

        var acceptBtn = document.getElementById('cookie-consent-accept');
        if (acceptBtn) {
            acceptBtn.addEventListener('click', function () {
                postConsent(true);
                hideBanner(banner);
            });
        }

        var declineBtn = document.getElementById('cookie-consent-decline');
        if (declineBtn) {
            declineBtn.addEventListener('click', function () {
                postConsent(false);
                hideBanner(banner);
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
