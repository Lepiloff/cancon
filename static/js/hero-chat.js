(function() {
    var heroInput = document.getElementById('hero-chat-input');
    var heroSend = document.getElementById('hero-chat-send');

    if (!heroInput) return;

    function sendHeroMessage() {
        if (!heroInput.value.trim()) return;
        var query = heroInput.value.trim();
        heroInput.value = '';
        if (window.openFullscreenChat) {
            window.openFullscreenChat(query);
            setTimeout(function() {
                var fsSend = document.getElementById('chat-fullscreen-send');
                if (fsSend) fsSend.click();
            }, 300);
        }
    }

    if (heroSend) {
        heroSend.addEventListener('click', sendHeroMessage);
    }
    heroInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendHeroMessage();
        }
    });

    // Suggestion chips
    var chips = document.querySelectorAll('.hero-chips__item');
    for (var i = 0; i < chips.length; i++) {
        chips[i].addEventListener('click', function() {
            var query = this.getAttribute('data-query');
            if (window.openFullscreenChat) {
                window.openFullscreenChat(query);
                setTimeout(function() {
                    var fsSend = document.getElementById('chat-fullscreen-send');
                    if (fsSend) fsSend.click();
                }, 300);
            }
        });
    }
})();
