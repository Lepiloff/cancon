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
    if (burger && nav) {
        burger.addEventListener('click', function() {
            burger.classList.toggle('header-v2__burger--active');
            nav.classList.toggle('header-v2__nav--open');
        });
    }
})();
