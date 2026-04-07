(() => {
  const normalizePath = (value) => {
    const url = new URL(value, window.location.origin);
    return url.pathname.replace(/\/+$/, '/') || '/';
  };

  const initNav = () => {
    const nav = document.querySelector('[data-dashboard-nav]');

    if (!nav) {
      return;
    }

    const links = Array.from(nav.querySelectorAll('a[href]'));
    const currentPath = window.location.pathname.replace(/\/+$/, '/') || '/';
    let activeLink = links.find((link) => normalizePath(link.getAttribute('href')) === currentPath);

    if (!activeLink) {
      activeLink = links.find((link) => currentPath.startsWith(normalizePath(link.getAttribute('href'))));
    }

    if (activeLink) {
      activeLink.classList.add('dashboard-nav__link--active');
      activeLink.setAttribute('aria-current', 'page');

      if (window.matchMedia('(max-width: 768px)').matches) {
        activeLink.scrollIntoView({
          block: 'nearest',
          inline: 'center',
        });
      }
    }
  };

  const initJournalAutocomplete = () => {
    const form = document.querySelector('[data-dashboard-journal-form]');

    if (!form) {
      return;
    }

    const endpoint = form.dataset.strainAutocompleteUrl;
    const emptyText = form.dataset.autocompleteEmptyText || '';
    const textInput = form.querySelector('input[name="strain_name_text"]');
    const hiddenInput = form.querySelector('input[name="strain_id"]');
    const results = form.querySelector('[data-autocomplete-results]');
    const clearButton = form.querySelector('[data-clear-strain]');

    if (!endpoint || !textInput || !hiddenInput || !results) {
      return;
    }

    let activeController = null;
    let lastQuery = '';
    let debounceTimer = null;

    const closeResults = () => {
      results.innerHTML = '';
      results.hidden = true;
    };

    const syncClearButton = () => {
      if (!clearButton) {
        return;
      }

      clearButton.hidden = !(hiddenInput.value || textInput.value.trim());
    };

    const applyChoice = (item) => {
      textInput.value = item.name;
      hiddenInput.value = item.id;
      syncClearButton();
      closeResults();
    };

    const renderResults = (items) => {
      results.innerHTML = '';

      if (!items.length) {
        const emptyState = document.createElement('div');
        emptyState.className = 'dashboard-autocomplete__empty';
        emptyState.textContent = emptyText;
        results.appendChild(emptyState);
        results.hidden = false;
        return;
      }

      items.forEach((item) => {
        const button = document.createElement('button');
        const name = document.createElement('span');
        const meta = document.createElement('span');

        button.type = 'button';
        button.className = 'dashboard-autocomplete__option';
        button.dataset.strainId = item.id;
        name.className = 'dashboard-autocomplete__name';
        name.textContent = item.name;
        meta.className = 'dashboard-autocomplete__meta';
        meta.textContent = item.category;
        button.appendChild(name);
        button.appendChild(meta);
        button.addEventListener('click', () => applyChoice(item));
        results.appendChild(button);
      });

      results.hidden = false;
    };

    const requestResults = (query) => {
      if (query === lastQuery) {
        return;
      }

      lastQuery = query;

      if (activeController) {
        activeController.abort();
      }

      activeController = new AbortController();
      const url = new URL(endpoint, window.location.origin);
      url.searchParams.set('q', query);

      fetch(url, {
        headers: {
          Accept: 'application/json',
        },
        signal: activeController.signal,
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error('autocomplete_failed');
          }
          return response.json();
        })
        .then((payload) => {
          if (textInput.value.trim() !== query) {
            return;
          }
          renderResults(payload.results || []);
        })
        .catch((error) => {
          if (error.name === 'AbortError') {
            return;
          }
          closeResults();
        });
    };

    textInput.addEventListener('input', () => {
      const query = textInput.value.trim();
      hiddenInput.value = '';
      syncClearButton();

      if (query.length < 2) {
        lastQuery = '';
        if (debounceTimer) {
          window.clearTimeout(debounceTimer);
        }
        closeResults();
        return;
      }

      if (debounceTimer) {
        window.clearTimeout(debounceTimer);
      }

      debounceTimer = window.setTimeout(() => {
        requestResults(query);
      }, 180);
    });

    document.addEventListener('click', (event) => {
      if (!form.contains(event.target)) {
        closeResults();
      }
    });

    textInput.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeResults();
      }
    });

    if (clearButton) {
      clearButton.addEventListener('click', () => {
        textInput.value = '';
        hiddenInput.value = '';
        lastQuery = '';
        syncClearButton();
        closeResults();
        textInput.focus();
      });
    }

    syncClearButton();
  };

  const initConfirmForms = () => {
    const forms = document.querySelectorAll('[data-confirm-form]');

    forms.forEach((form) => {
      form.addEventListener('submit', (event) => {
        const message = form.dataset.confirmMessage || '';
        if (!window.confirm(message)) {
          event.preventDefault();
        }
      });
    });
  };

  initNav();
  initJournalAutocomplete();
  initConfirmForms();
})();
