(function() {
    var heroInput = document.getElementById('hero-chat-input');
    var heroSend = document.getElementById('hero-chat-send');

    if (!heroInput) return;

    function waitForChatFunction(callback) {
        if (window.openFullscreenChat) {
            callback();
            return;
        }

        var attempts = 0;
        var maxAttempts = 50;
        var checkInterval = setInterval(function() {
            attempts++;
            if (window.openFullscreenChat || attempts >= maxAttempts) {
                clearInterval(checkInterval);
                if (window.openFullscreenChat) {
                    callback();
                }
            }
        }, 100);
    }

    function sendHeroMessage() {
        if (!heroInput.value.trim()) return;
        var query = heroInput.value.trim();
        heroInput.value = '';
        waitForChatFunction(function() {
            window.openFullscreenChat(query);
            setTimeout(function() {
                var fsSend = document.getElementById('chat-fullscreen-send');
                if (fsSend) fsSend.click();
            }, 300);
        });
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
            waitForChatFunction(function() {
                window.openFullscreenChat(query);
                setTimeout(function() {
                    var fsSend = document.getElementById('chat-fullscreen-send');
                    if (fsSend) fsSend.click();
                }, 300);
            });
        });
    }
})();
