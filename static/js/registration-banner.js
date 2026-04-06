(function () {
    'use strict';

    var cfg = window.RegistrationBannerConfig || {};

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function setCookie(name, value, maxAgeSeconds) {
        var cookie = name + '=' + encodeURIComponent(value) + '; path=/; samesite=lax';
        if (maxAgeSeconds) {
            cookie += '; max-age=' + String(maxAgeSeconds);
        }
        document.cookie = cookie;
    }

    function isVisible(el) {
        return !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
    }

    function showBanner(banner) {
        requestAnimationFrame(function () {
            banner.classList.add('registration-banner--visible');
            var firstAction = banner.querySelector('.registration-banner__btn--primary, .registration-banner__btn--secondary');
            if (firstAction && firstAction.focus) {
                firstAction.focus({ preventScroll: true });
            }
        });
    }

    function hideBanner(banner) {
        banner.classList.add('registration-banner--hiding');
        banner.classList.remove('registration-banner--visible');

        var onEnd = function () {
            banner.removeEventListener('transitionend', onEnd);
            banner.remove();
        };

        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            banner.remove();
        } else {
            banner.addEventListener('transitionend', onEnd);
            setTimeout(function () {
                try { banner.remove(); } catch (e) {}
            }, 700);
        }
    }

    function postDismiss() {
        var url = cfg.dismissUrl || '';
        var payload = JSON.stringify({ dismissed: true });

        if (!url) {
            return Promise.resolve();
        }

        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: payload
        }).then(function (response) {
            if (!response.ok) {
                throw new Error('Dismiss request failed');
            }
        });
    }

    function shouldShow() {
        if (!cfg.showBanner) return false;
        if (cfg.cookieBannerVisible) return false;

        var cookieName = cfg.dismissCookieName || 'reg_banner_dismissed';
        if (getCookie(cookieName)) return false;

        return true;
    }

    function init() {
        if (!shouldShow()) return;

        var banner = document.getElementById('registration-banner');
        if (!banner) return;

        if (isVisible(document.getElementById('cookie-consent-banner'))) {
            return;
        }

        showBanner(banner);

        var dismissBtn = document.getElementById('registration-banner-dismiss');
        if (dismissBtn) {
            dismissBtn.addEventListener('click', function () {
                var cookieName = cfg.dismissCookieName || 'reg_banner_dismissed';
                var maxAge = parseInt(cfg.dismissCookieAgeSeconds, 10) || 604800;

                setCookie(cookieName, '1', maxAge);
                postDismiss().catch(function () {
                    // Keep the local cooldown even if the network call fails.
                }).finally(function () {
                    hideBanner(banner);
                });
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
