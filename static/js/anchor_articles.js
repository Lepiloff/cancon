    document.addEventListener("DOMContentLoaded", function() {
        const links = document.querySelectorAll('.anchor-links a');
        const sections = Array.from(links)
            .map(link => document.querySelector(link.getAttribute('href')))
            .filter(section => section !== null); // Фильтруем возможные null

        let scrollTicking = false;

        function onScroll() {
            const scrollPosition = window.scrollY + 150; // Смещение для точности

            let activeSection = sections[0];

            for (let section of sections) {
                if (section.offsetTop <= scrollPosition) {
                    activeSection = section;
                } else {
                    break;
                }
            }

            links.forEach(link => {
                if (link.getAttribute('href') === `#${activeSection.id}`) {
                    link.classList.add('active');
                } else {
                    link.classList.remove('active');
                }
            });
        }

        window.addEventListener('scroll', function() {
            if (!scrollTicking) {
                requestAnimationFrame(function() {
                    onScroll();
                    scrollTicking = false;
                });
                scrollTicking = true;
            }
        });
        onScroll(); // Инициализация при загрузке страницы
    });