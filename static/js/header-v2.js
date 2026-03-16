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
        nav.classList.add('header-v2__nav--open');
        document.body.classList.add('mobile-nav-open');
    }

    function closeNav() {
        burger.classList.remove('header-v2__burger--active');
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
})();
