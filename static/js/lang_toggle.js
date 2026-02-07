// Simple enhancement for language toggle: keyboard focus and click delegation
(function() {
  try {
    var toggle = document.querySelector('.lang-toggle');
    if (!toggle) return;

    toggle.setAttribute('tabindex', '0');
    toggle.addEventListener('keydown', function(e) {
      // Enter or Space navigates to the inactive language link
      if (e.key === 'Enter' || e.key === ' ') {
        var inactive = toggle.querySelector('.lang-toggle__option.is-inactive');
        if (inactive && inactive.href) {
          e.preventDefault();
          window.location.assign(inactive.href);
        }
      }
    });

    // Optional: click anywhere on the pill goes to inactive link
    toggle.addEventListener('click', function(e) {
      var inactive = toggle.querySelector('.lang-toggle__option.is-inactive');
      if (!inactive) return;
      // if clicked a link, let it proceed
      if (e.target && e.target.tagName === 'A') return;
      window.location.assign(inactive.href);
    });
  } catch (err) {
    // no-op; don't break the page
  }
})();
