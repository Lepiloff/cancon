(function() {
    // Header scroll effect
    var header = document.getElementById('header-v2');
    if (header) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                header.classList.add('header-v2--scrolled');
            } else {
                header.classList.remove('header-v2--scrolled');
            }
        });
    }

    // Mobile burger menu
    var burger = document.getElementById('burger-btn');
    var nav = document.getElementById('main-nav');
    var closeBtn = document.getElementById('nav-close-btn');

    function openNav() {
        burger.classList.add('header-v2__burger--active');
        burger.setAttribute('aria-expanded', 'true');
        nav.classList.add('header-v2__nav--open');
        document.body.classList.add('mobile-nav-open');
    }

    function closeNav() {
        burger.classList.remove('header-v2__burger--active');
        burger.setAttribute('aria-expanded', 'false');
        nav.classList.remove('header-v2__nav--open');
        document.body.classList.remove('mobile-nav-open');
    }

    if (burger && nav) {
        burger.addEventListener('click', function() {
            if (nav.classList.contains('header-v2__nav--open')) {
                closeNav();
            } else {
                openNav();
            }
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeNav);
    }

    // Close mobile nav when clicking a nav link
    if (nav) {
        nav.querySelectorAll('.header-v2__nav-link').forEach(function(link) {
            link.addEventListener('click', closeNav);
        });
    }

    // Active nav link detection
    var path = window.location.pathname;
    var langPrefix = path.match(/^\/en(\/|$)/) ? '/en' : '';
    var cleanPath = langPrefix ? path.replace(/^\/en/, '') : path;
    var navLinks = document.querySelectorAll('.header-v2__nav-link[data-nav]');
    var matched = false;

    navLinks.forEach(function(link) {
        var key = link.getAttribute('data-nav');
        var isActive = false;

        if (key === 'home' && (cleanPath === '/' || cleanPath === '')) {
            isActive = true;
        } else if (key === 'strain' && cleanPath.match(/^\/(strains?|strain\/)/)) {
            isActive = true;
        } else if (key === 'terpene' && cleanPath.match(/^\/(terpenes?|terpene\/)/)) {
            isActive = true;
        } else if (key === 'article' && cleanPath.match(/^\/(articles?|article\/)/)) {
            isActive = true;
        }

        if (isActive) {
            link.classList.add('header-v2__nav-link--active');
            link.setAttribute('aria-current', 'page');
            matched = true;
        }
    });
})();
