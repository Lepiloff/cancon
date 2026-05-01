(function() {
    var heroInput = document.getElementById('hero-chat-input');
    var heroSend = document.getElementById('hero-chat-send');

    if (!heroInput) return;

    // Rotate placeholder every 5s while input is empty
    if (window.ChatPlaceholderRotator) {
        window.ChatPlaceholderRotator.attach(heroInput);
    }

    function openChatWithQuery(query) {
        if (!window.openFullscreenChat) return;
        window.openFullscreenChat(query);
        setTimeout(function() {
            var fsSend = document.getElementById('chat-fullscreen-send');
            if (fsSend) fsSend.click();
        }, 300);
    }

    function sendHeroMessage() {
        var query = heroInput.value.trim();
        if (!query) return;
        heroInput.value = '';
        openChatWithQuery(query);
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
            openChatWithQuery(this.getAttribute('data-query'));
        });
    }
})();
