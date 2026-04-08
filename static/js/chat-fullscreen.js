/**
 * Fullscreen Chat for AI Budtender.
 *
 * Requires window.ChatFullscreenConfig with translated error strings and URLs:
 *   { chatUrl, streamUrl, signupUrl, isAuthenticated, errRateLimit,
 *     errRateLimitCta, errRateLimitCtaLabel, errUnavailable, errServer,
 *     errConnection, errNoInternet, resumeChat }
 */
(function() {
    var cfg = window.ChatFullscreenConfig || {};
    var chatUrl = cfg.chatUrl || '';
    var streamUrl = cfg.streamUrl || '';
    var signupUrl = cfg.signupUrl || '';
    var isAuthenticated = !!cfg.isAuthenticated;

    var fullscreen = document.getElementById('chat-fullscreen');
    var fsMessages = document.getElementById('chat-fullscreen-messages');
    var fsInput    = document.getElementById('chat-fullscreen-input');
    var fsSend     = document.getElementById('chat-fullscreen-send');
    var fsClose    = document.getElementById('chat-fullscreen-close');
    var resumeFab  = document.getElementById('chat-resume-fab');

    if (!fullscreen) return; // chat not enabled on this page

    // --- Session persistence constants -------------------------------------------

    var STORAGE_KEY_HISTORY  = 'ai-budtender-chat-history';
    var STORAGE_KEY_TIMESTAMP = 'ai-budtender-chat-ts';
    var SESSION_TTL_MS = 60 * 60 * 1000; // 1 hour

    // --- Open / Close -----------------------------------------------------------

    var previouslyFocused = null;
    var historyRestored = false;

    function openFullscreenChat(prefillText) {
        previouslyFocused = document.activeElement;

        // Restore chat history on first open if not already done
        if (!historyRestored) {
            restoreChatHistory();
            historyRestored = true;
        }

        fullscreen.classList.add('chat-fullscreen--active');
        fullscreen.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        if (prefillText && fsInput) {
            fsInput.value = prefillText;
            fsInput.focus();
        } else if (fsInput) {
            fsInput.focus();
        }

        // Scroll to bottom after restore
        if (fsMessages) {
            fsMessages.scrollTop = fsMessages.scrollHeight;
        }

        updateResumeFab();
    }

    function closeFullscreenChat() {
        fullscreen.classList.remove('chat-fullscreen--active');
        fullscreen.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        if (previouslyFocused && previouslyFocused.focus) {
            previouslyFocused.focus();
        }
        updateResumeFab();
    }

    if (fsClose) {
        fsClose.addEventListener('click', closeFullscreenChat);
    }

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && fullscreen.classList.contains('chat-fullscreen--active')) {
            closeFullscreenChat();
        }
    });

    // Expose for other scripts (hero section, strains page CTA)
    window.openFullscreenChat = openFullscreenChat;

    // --- Helpers -----------------------------------------------------------------

    function getPageLanguage() {
        var lang = document.documentElement.lang || 'es';
        return lang.split('-')[0].toLowerCase();
    }

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

    function getSessionId() {
        return localStorage.getItem('ai-budtender-session-id') ||
               localStorage.getItem('ai_budtender_session_id') || null;
    }

    function setSessionId(id) {
        localStorage.setItem('ai-budtender-session-id', id);
        localStorage.setItem('ai_budtender_session_id', id);
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // --- Chat history persistence ------------------------------------------------

    function isSessionExpired() {
        var ts = localStorage.getItem(STORAGE_KEY_TIMESTAMP);
        if (!ts) return true;
        return (Date.now() - parseInt(ts, 10)) > SESSION_TTL_MS;
    }

    function touchSessionTimestamp() {
        localStorage.setItem(STORAGE_KEY_TIMESTAMP, String(Date.now()));
    }

    function getChatHistory() {
        if (isSessionExpired()) {
            clearChatSession();
            return [];
        }
        try {
            var raw = localStorage.getItem(STORAGE_KEY_HISTORY);
            return raw ? JSON.parse(raw) : [];
        } catch(e) {
            return [];
        }
    }

    function saveChatHistory(history) {
        try {
            // Keep max 50 messages to avoid localStorage bloat
            var trimmed = history.slice(-50);
            localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(trimmed));
            touchSessionTimestamp();
        } catch(e) {
            // localStorage full — silently fail
        }
    }

    function appendToHistory(entry) {
        var history = getChatHistory();
        history.push(entry);
        saveChatHistory(history);
    }

    function clearChatSession() {
        localStorage.removeItem(STORAGE_KEY_HISTORY);
        localStorage.removeItem(STORAGE_KEY_TIMESTAMP);
        localStorage.removeItem('ai-budtender-session-id');
        localStorage.removeItem('ai_budtender_session_id');
    }

    function hasActiveSession() {
        if (isSessionExpired()) {
            clearChatSession();
            return false;
        }
        var history = getChatHistory();
        return history.length > 0;
    }

    function restoreChatHistory() {
        var history = getChatHistory();
        if (!history.length) return;

        // Hide welcome message
        var welcome = fsMessages.querySelector('.chat-fullscreen__welcome');
        if (welcome) welcome.style.display = 'none';

        for (var i = 0; i < history.length; i++) {
            var entry = history[i];
            if (entry.role === 'user') {
                addMessageToFullscreen('user', entry.text, true);
            } else if (entry.role === 'assistant') {
                var msg = addMessageToFullscreen('assistant', '', true);
                var textEl = msg.querySelector('.chat-fullscreen__msg-text');
                if (textEl) {
                    textEl.innerHTML = parseSimpleMarkdown(entry.text);
                }
                if (entry.strains && entry.strains.length) {
                    renderStrainCards(msg, entry.strains);
                }
            }
        }
    }

    // --- Resume FAB --------------------------------------------------------------

    function updateResumeFab() {
        if (!resumeFab) return;
        var chatOpen = fullscreen.classList.contains('chat-fullscreen--active');
        if (!chatOpen && hasActiveSession()) {
            resumeFab.classList.add('chat-resume-fab--visible');
        } else {
            resumeFab.classList.remove('chat-resume-fab--visible');
        }
    }

    if (resumeFab) {
        resumeFab.addEventListener('click', function() {
            openFullscreenChat('');
        });
    }

    // Check on page load
    updateResumeFab();

    // --- UI builders -------------------------------------------------------------

    function showTypingIndicator() {
        var welcome = fsMessages.querySelector('.chat-fullscreen__welcome');
        if (welcome) welcome.style.display = 'none';

        var typing = document.createElement('div');
        typing.className = 'chat-fullscreen__msg chat-fullscreen__msg--assistant chat-fullscreen__msg--typing';
        typing.innerHTML = '<div class="chat-fullscreen__typing-indicator">' +
            '<span class="chat-fullscreen__typing-dot"></span>' +
            '<span class="chat-fullscreen__typing-dot"></span>' +
            '<span class="chat-fullscreen__typing-dot"></span>' +
            '</div>';
        fsMessages.appendChild(typing);
        fsMessages.scrollTop = fsMessages.scrollHeight;
        return typing;
    }

    function addMessageToFullscreen(role, text, skipPersist) {
        var welcome = fsMessages.querySelector('.chat-fullscreen__welcome');
        if (welcome) welcome.style.display = 'none';

        var msg = document.createElement('div');
        msg.className = 'chat-fullscreen__msg chat-fullscreen__msg--' + role;
        msg.innerHTML = '<div class="chat-fullscreen__msg-text">' + escapeHtml(text) + '</div>';
        fsMessages.appendChild(msg);
        fsMessages.scrollTop = fsMessages.scrollHeight;

        // Persist user messages immediately
        if (!skipPersist && role === 'user') {
            appendToHistory({ role: 'user', text: text });
        }

        return msg;
    }

    function addErrorMessage(text) {
        var msg = document.createElement('div');
        msg.className = 'chat-fullscreen__msg chat-fullscreen__msg--error';
        msg.innerHTML = '<div class="chat-fullscreen__msg-text chat-fullscreen__msg-error-text">' +
            '<div class="chat-fullscreen__msg-error-copy">' +
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
                '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>' +
                '<span>' + escapeHtml(text) + '</span>' +
            '</div>' +
            '</div>';
        fsMessages.appendChild(msg);
        fsMessages.scrollTop = fsMessages.scrollHeight;
    }

    function addRateLimitMessage() {
        var ctaHtml = '';
        var ctaCopyHtml = '';
        if (!isAuthenticated && signupUrl) {
            ctaHtml = '<a class="chat-fullscreen__error-cta" href="' + escapeHtml(signupUrl) + '">' +
                escapeHtml(cfg.errRateLimitCtaLabel || 'Crear cuenta') +
                '</a>';
            ctaCopyHtml = '<div class="chat-fullscreen__msg-error-cta-copy">' +
                escapeHtml(cfg.errRateLimitCta || 'Create an account to keep chatting.') +
                '</div>';
        }
        var msg = document.createElement('div');
        msg.className = 'chat-fullscreen__msg chat-fullscreen__msg--error';
        msg.innerHTML = '<div class="chat-fullscreen__msg-text chat-fullscreen__msg-error-text">' +
            '<div class="chat-fullscreen__msg-error-copy">' +
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
                '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>' +
                '<span>' + escapeHtml(cfg.errRateLimit || 'Rate limit reached') + '</span>' +
            '</div>' +
            (ctaCopyHtml ? ctaCopyHtml : '') +
            (ctaHtml ? '<div class="chat-fullscreen__msg-error-cta-wrap">' + ctaHtml + '</div>' : '') +
            '</div>';
        fsMessages.appendChild(msg);
        fsMessages.scrollTop = fsMessages.scrollHeight;
    }

    // --- Strain cards ------------------------------------------------------------

    function strainUrl(absoluteUrl) {
        if (!absoluteUrl) return '#';
        try { return new URL(absoluteUrl).pathname; }
        catch(e) { return absoluteUrl; }
    }

    function createStrainCardHTML(strain) {
        var cat = (strain.category || '').toLowerCase();
        var badgeClass = 'chat-strain-card__badge--' +
            (cat === 'indica' || cat === 'sativa' || cat === 'hybrid' ? cat : 'hybrid');

        var cannabinoids = '';
        var cann = [
            {key: 'thc', label: 'THC'},
            {key: 'cbd', label: 'CBD'},
            {key: 'cbg', label: 'CBG'}
        ];
        for (var c = 0; c < cann.length; c++) {
            var val = strain[cann[c].key];
            if (val && parseFloat(val) > 0) {
                cannabinoids += '<span class="chat-strain-card__cannabinoid">' +
                    '<span class="chat-strain-card__cannabinoid-label">' + cann[c].label + '</span>' +
                    '<span class="chat-strain-card__cannabinoid-value">' + escapeHtml(parseFloat(val).toFixed(1)) + '%</span>' +
                    '</span>';
            }
        }

        var effects = '';
        if (strain.feelings && strain.feelings.length) {
            var top = strain.feelings.slice(0, 3);
            for (var i = 0; i < top.length; i++) {
                effects += '<span class="chat-strain-card__effect-tag">' + escapeHtml(top[i].name) + '</span>';
            }
        }

        var flavors = '';
        if (strain.flavors && strain.flavors.length) {
            var topF = strain.flavors.slice(0, 2);
            for (var j = 0; j < topF.length; j++) {
                flavors += '<span class="chat-strain-card__flavor-tag">' + escapeHtml(topF[j].name) + '</span>';
            }
        }

        return '<a href="' + escapeHtml(strainUrl(strain.url)) + '" class="chat-strain-card" target="_blank" rel="noopener">' +
            '<div class="chat-strain-card__header">' +
                '<span class="chat-strain-card__name">' + escapeHtml(strain.name || '') + '</span>' +
                '<span class="chat-strain-card__badge ' + badgeClass + '">' + escapeHtml(strain.category || '') + '</span>' +
            '</div>' +
            (cannabinoids ? '<div class="chat-strain-card__cannabinoids">' + cannabinoids + '</div>' : '') +
            (effects ? '<div class="chat-strain-card__effects">' + effects + '</div>' : '') +
            (flavors ? '<div class="chat-strain-card__flavors">' + flavors + '</div>' : '') +
            '</a>';
    }

    function renderStrainCards(msgElement, strains) {
        if (!strains || !strains.length || !msgElement) return;
        var container = document.createElement('div');
        container.className = 'chat-strain-cards';
        var html = '';
        for (var i = 0; i < strains.length; i++) {
            html += createStrainCardHTML(strains[i]);
        }
        container.innerHTML = html;
        msgElement.appendChild(container);
        fsMessages.scrollTop = fsMessages.scrollHeight;
    }

    // --- Streaming bubble --------------------------------------------------------

    function createStreamingBubble(strains) {
        var welcome = fsMessages.querySelector('.chat-fullscreen__welcome');
        if (welcome) welcome.style.display = 'none';

        var msg = document.createElement('div');
        msg.className = 'chat-fullscreen__msg chat-fullscreen__msg--assistant';
        msg.innerHTML = '<div class="chat-fullscreen__msg-text">' +
            '<span class="chat-fullscreen__stream-text"></span>' +
            '<span class="chat-fullscreen__streaming-cursor"></span>' +
            '</div>';
        fsMessages.appendChild(msg);

        if (strains && strains.length) {
            renderStrainCards(msg, strains);
        }

        fsMessages.scrollTop = fsMessages.scrollHeight;
        return {
            bubble: msg,
            textSpan: msg.querySelector('.chat-fullscreen__stream-text')
        };
    }

    function parseSimpleMarkdown(str) {
        if (typeof str !== 'string') return '';
        return escapeHtml(str)
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    function finalizeStreamingBubble(bubble) {
        if (!bubble) return;
        var cursor = bubble.querySelector('.chat-fullscreen__streaming-cursor');
        if (cursor) cursor.remove();
        var textSpan = bubble.querySelector('.chat-fullscreen__stream-text');
        if (textSpan && textSpan.textContent) {
            textSpan.innerHTML = parseSimpleMarkdown(textSpan.textContent);
        }
    }

    // --- Send message (SSE streaming with blocking fallback) ---------------------

    var fsIsSending = false;
    var lastSentMessage = '';
    var lastSentTime = 0;
    var DUPLICATE_COOLDOWN_MS = 2000;

    function setSendingState(sending) {
        fsIsSending = sending;
        if (fsSend) {
            fsSend.disabled = sending;
            if (sending) {
                fsSend.classList.add('chat-fullscreen__send--disabled');
            } else {
                fsSend.classList.remove('chat-fullscreen__send--disabled');
            }
        }
    }

    function persistAssistantMessage(text, strains) {
        appendToHistory({
            role: 'assistant',
            text: text,
            strains: strains || []
        });
        updateResumeFab();
    }

    function sendFullscreenMessage() {
        if (fsIsSending) return;
        if (!fsInput || !fsInput.value.trim()) return;

        var message = fsInput.value.trim();

        // Prevent duplicate messages within cooldown window
        var now = Date.now();
        if (message === lastSentMessage && (now - lastSentTime) < DUPLICATE_COOLDOWN_MS) {
            return;
        }

        setSendingState(true);
        lastSentMessage = message;
        lastSentTime = now;

        addMessageToFullscreen('user', message);
        fsInput.value = '';
        fsInput.style.height = 'auto';

        var typingEl = showTypingIndicator();
        function unlockSend() { setSendingState(false); }

        if (!chatUrl || !streamUrl) {
            typingEl.remove();
            addErrorMessage(cfg.errServer || 'Server error');
            unlockSend();
            return;
        }

        var payload = {
            message: message,
            language: getPageLanguage(),
            source_platform: 'cannamente'
        };
        var sid = getSessionId();
        if (sid) payload.session_id = sid;

        var headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken') || ''
        };

        function handleBlockingFallback(onDone) {
            var fbTyping = showTypingIndicator();
            fetch(chatUrl, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(payload)
            }).then(function(r) { return r.json(); }).then(function(data) {
                fbTyping.remove();
                if (data.response) {
                    var fbMsg = addMessageToFullscreen('assistant', data.response);
                    if (data.session_id) setSessionId(data.session_id);
                    var fbStrains = data.recommended_strains || [];
                    if (fbStrains.length) {
                        renderStrainCards(fbMsg, fbStrains);
                    }
                    persistAssistantMessage(data.response, fbStrains);
                } else if (data.error) {
                    addErrorMessage(data.error);
                } else {
                    addErrorMessage(cfg.errServer || 'Server error');
                }
                unlockSend();
            }).catch(function() {
                fbTyping.remove();
                addErrorMessage(onDone || cfg.errServer || 'Server error');
                unlockSend();
            });
        }

        fetch(streamUrl, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        }).then(function(response) {
            if (response.status === 429) {
                typingEl.remove();
                addRateLimitMessage();
                unlockSend();
                return;
            }
            if (response.status === 503) {
                typingEl.remove();
                addErrorMessage(cfg.errUnavailable || 'Service unavailable');
                unlockSend();
                return;
            }
            if (!response.ok) {
                typingEl.remove();
                handleBlockingFallback(cfg.errServer);
                return;
            }

            // SSE Streaming
            var reader = response.body.getReader();
            var decoder = new TextDecoder();
            var buffer = '';
            var streamBubble = null;
            var textSpan = null;
            var fullText = '';
            var metadataResponse = '';
            var streamStrains = null;
            var finalized = false;

            function finalize() {
                if (finalized) return;
                finalized = true;
                // If no streamed text but metadata contained a response, use it
                if (!fullText && metadataResponse) {
                    fullText = metadataResponse;
                    if (textSpan) textSpan.textContent = fullText;
                }
                // Handle empty response: stream ended without any text
                if (!fullText && streamBubble) {
                    streamBubble.remove();
                    addErrorMessage(cfg.errServer || 'Server error');
                } else if (!fullText && !streamBubble) {
                    addErrorMessage(cfg.errServer || 'Server error');
                } else {
                    finalizeStreamingBubble(streamBubble);
                    persistAssistantMessage(fullText, streamStrains);
                }
                unlockSend();
            }

            function processLines(text) {
                var lines = text.split('\n');
                for (var i = 0; i < lines.length; i++) {
                    var line = lines[i];
                    if (!line.startsWith('data: ')) continue;
                    try {
                        var data = JSON.parse(line.slice(6));

                        if (data.type === 'metadata') {
                            if (data.session_id) setSessionId(data.session_id);
                            if (data.data && data.data.session_id) setSessionId(data.data.session_id);

                            var strains = null;
                            if (data.data && data.data.recommended_strains) strains = data.data.recommended_strains;
                            if (data.recommended_strains) strains = data.recommended_strains;
                            streamStrains = strains;

                            // Capture response text from metadata (non-search branches send it here)
                            if (data.data && data.data.response) metadataResponse = data.data.response;

                            typingEl.remove();
                            var created = createStreamingBubble(strains);
                            streamBubble = created.bubble;
                            textSpan = created.textSpan;

                        } else if (data.type === 'response_chunk') {
                            var chunk = data.text || data.content || '';
                            if (chunk) {
                                if (!streamBubble) {
                                    typingEl.remove();
                                    var created2 = createStreamingBubble(null);
                                    streamBubble = created2.bubble;
                                    textSpan = created2.textSpan;
                                }
                                fullText += chunk;
                                textSpan.textContent = fullText;
                                fsMessages.scrollTop = fsMessages.scrollHeight;
                            }

                        } else if (data.type === 'error') {
                            typingEl.remove();
                            if (streamBubble) streamBubble.remove();
                            addErrorMessage(data.message || cfg.errConnection || 'Connection error');
                            finalize();
                            return;

                        } else if (data.type === 'done') {
                            finalize();
                        }
                    } catch(e) {
                        // skip malformed JSON
                    }
                }
            }

            function readChunk() {
                reader.read().then(function(result) {
                    if (result.done) {
                        if (buffer.trim()) processLines(buffer);
                        try { typingEl.remove(); } catch(e) {}
                        finalize();
                        return;
                    }
                    buffer += decoder.decode(result.value, {stream: true});
                    var lines = buffer.split('\n');
                    buffer = lines.pop();
                    processLines(lines.join('\n'));
                    readChunk();
                }).catch(function() {
                    if (!streamBubble) typingEl.remove();
                    if (!fullText && streamBubble) {
                        streamBubble.remove();
                        addErrorMessage(cfg.errConnection || 'Connection error');
                    }
                    finalize();
                });
            }

            readChunk();

        }).catch(function() {
            typingEl.remove();
            handleBlockingFallback(cfg.errNoInternet || 'No internet connection');
        });
    }

    // --- Input bindings ----------------------------------------------------------

    if (fsSend) {
        fsSend.addEventListener('click', sendFullscreenMessage);
    }
    if (fsInput) {
        fsInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendFullscreenMessage();
            }
        });
        fsInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
    }

    // --- Expired session cleanup on load -----------------------------------------
    if (isSessionExpired()) {
        clearChatSession();
    }
})();
