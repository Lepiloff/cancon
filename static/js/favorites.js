(function() {
    'use strict';

    var cfg = window.FavoritesConfig || {};
    var toggleUrl = cfg.toggleUrl || '';
    var statusUrl = cfg.statusUrl || '';

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

    function getButtons(root) {
        var scope = root || document;
        return scope.querySelectorAll('[data-favorite-button]');
    }

    function setButtonState(button, isActive) {
        var active = !!isActive;
        var label = button.querySelector('[data-favorite-label]');

        button.classList.toggle('is-active', active);
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
        button.setAttribute(
            'aria-label',
            active ? (cfg.removeLabel || '') : (cfg.addLabel || '')
        );
        button.setAttribute(
            'title',
            active ? (cfg.removeLabel || '') : (cfg.addLabel || '')
        );
        button.dataset.favoriteActive = active ? 'true' : 'false';
        button.dataset.favoriteHydrated = 'true';

        if (label) {
            label.textContent = active ? (cfg.activeText || '') : (cfg.defaultText || '');
        }
    }

    function collectPendingIds(root) {
        var buttons = getButtons(root);
        var ids = [];
        var seen = {};

        for (var i = 0; i < buttons.length; i++) {
            var button = buttons[i];
            var strainId = button.dataset.strainId;

            if (!strainId || button.dataset.favoriteHydrated === 'true' || seen[strainId]) {
                continue;
            }

            seen[strainId] = true;
            ids.push(strainId);
        }

        return ids;
    }

    function hydrateButtons(root) {
        if (!cfg.isAuthenticated || !statusUrl) {
            return;
        }

        var ids = collectPendingIds(root);
        if (!ids.length) {
            return;
        }

        var requestedIds = {};
        for (var k = 0; k < ids.length; k++) {
            requestedIds[String(ids[k])] = true;
        }

        fetch(statusUrl + '?strain_ids=' + encodeURIComponent(ids.join(',')), {
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Favorite status request failed');
                }
                return response.json();
            })
            .then(function(data) {
                var favorites = {};
                var favoriteIds = data.favorites || [];

                for (var i = 0; i < favoriteIds.length; i++) {
                    favorites[String(favoriteIds[i])] = true;
                }

                var buttons = getButtons(root);
                for (var j = 0; j < buttons.length; j++) {
                    var button = buttons[j];
                    var strainId = button.dataset.strainId;
                    if (!strainId || !requestedIds[strainId]) {
                        continue;
                    }
                    setButtonState(button, !!favorites[strainId]);
                }
            })
            .catch(function() {
                // Keep default visual state if hydration fails.
            });
    }

    function toggleFavorite(button) {
        if (!cfg.isAuthenticated || !toggleUrl) {
            return;
        }

        var strainId = button.dataset.strainId;
        if (!strainId || button.dataset.favoriteBusy === 'true') {
            return;
        }

        button.dataset.favoriteBusy = 'true';
        button.classList.add('is-busy');

        fetch(toggleUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || '',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                strain_id: Number(strainId)
            })
        })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Favorite toggle request failed');
                }
                return response.json();
            })
            .then(function(data) {
                setButtonState(button, data.status === 'added');
            })
            .catch(function() {
                window.console.error(cfg.errorText || 'Favorite update failed');
            })
            .finally(function() {
                button.dataset.favoriteBusy = 'false';
                button.classList.remove('is-busy');
            });
    }

    function observeNewButtons() {
        if (!cfg.isAuthenticated || !window.MutationObserver) {
            return;
        }

        var observer = new MutationObserver(function(mutations) {
            for (var i = 0; i < mutations.length; i++) {
                var addedNodes = mutations[i].addedNodes;
                for (var j = 0; j < addedNodes.length; j++) {
                    var node = addedNodes[j];
                    if (!node.querySelectorAll) {
                        continue;
                    }

                    if (node.matches && node.matches('[data-favorite-button]')) {
                        hydrateButtons(node.parentNode || document);
                        continue;
                    }

                    if (node.querySelector('[data-favorite-button]')) {
                        hydrateButtons(node);
                    }
                }
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    function handleClick(event) {
        var button = event.target.closest('[data-favorite-button]');
        if (!button) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        toggleFavorite(button);
    }

    function init() {
        var buttons = getButtons();
        if (!buttons.length) {
            return;
        }

        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i].dataset.favoriteServerState === 'true') {
                setButtonState(buttons[i], buttons[i].dataset.favoriteActive === 'true');
            }
        }

        hydrateButtons(document);
        observeNewButtons();
        document.addEventListener('click', handleClick);
        window.refreshFavoriteButtons = hydrateButtons;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
