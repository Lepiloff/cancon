/**
 * AI Budtender Chat Widget
 * Real-time cannabis strain recommendations with WebSocket support
 */

// Translations for chat error messages (not in Django i18n)
const CHAT_ERROR_TRANSLATIONS = {
    en: {
        connectionError: 'Sorry, I cannot connect to the AI service right now. Please check your internet connection and try again.',
        rateLimitExceeded: 'Too many requests. Please try again in {time}.',
        rateLimitGeneric: 'Too many requests. Please wait a moment before trying again.',
        serviceUnavailable: 'Chat service is currently unavailable. Please try again later.',
        serverError: 'The AI service is temporarily unavailable. Please try again in a few moments.',
        genericError: 'Sorry, something went wrong. Please try again or refresh the page.',
        sessionRestored: 'Session restored',
        basicMode: 'Basic mode',
        conflictsResolved: 'Conflicts resolved',
        confidence: 'Confidence',
        followUpQuestion: 'Follow-up question',
        comparingOptions: 'Comparing options',
        clarifyingDoubts: 'Clarifying doubts',
        newSearch: 'New search'
    },
    es: {
        connectionError: 'Lo siento, no puedo conectar con el servicio de IA en este momento. Por favor, verifica tu conexión a internet e intenta de nuevo.',
        rateLimitExceeded: 'Demasiadas solicitudes. Por favor, intenta de nuevo en {time}.',
        rateLimitGeneric: 'Demasiadas solicitudes. Por favor, espera un momento antes de intentar de nuevo.',
        serviceUnavailable: 'El servicio de chat no está disponible actualmente. Por favor, intenta más tarde.',
        serverError: 'El servicio de IA no está disponible temporalmente. Por favor, intenta de nuevo en unos momentos.',
        genericError: 'Lo siento, algo salió mal. Por favor, intenta de nuevo o recarga la página.',
        sessionRestored: 'Sesión restaurada',
        basicMode: 'Modo básico',
        conflictsResolved: 'Conflictos resueltos',
        confidence: 'Confianza',
        followUpQuestion: 'Pregunta de seguimiento',
        comparingOptions: 'Comparando opciones',
        clarifyingDoubts: 'Aclarando dudas',
        newSearch: 'Nueva búsqueda'
    }
};

// Chat UI translations
const CHAT_UI_TRANSLATIONS = {
    en: {
        botName: 'AI Budtender',
        botRole: 'Cannabis strain expert',
        status: 'Online',
        welcomeTitle: 'Welcome to AI Budtender!',
        welcomeMessage: "I'm here to help you find the perfect cannabis strain based on your needs, preferences, and desired effects.",
        quickActions: {
            relaxation: 'Relaxation',
            creativity: 'Creativity',
            sleep: 'Sleep',
            energy: 'Energy',
            painRelief: 'Pain Relief'
        },
        quickMessages: {
            relaxation: "What's good for relaxation?",
            creativity: "I need something for creativity",
            sleep: "What helps with sleep?",
            energy: "Show me energizing strains",
            painRelief: "What's good for pain relief?"
        },
        connected: 'Connected',
        connecting: 'Connecting...',
        disconnected: 'Disconnected',
        offline: 'Offline'
    },
    es: {
        botName: 'Asistente IA Cannabis',
        botRole: 'Experto en cepas de cannabis',
        status: 'En línea',
        welcomeTitle: '¡Bienvenido al Asistente IA Cannabis!',
        welcomeMessage: 'Estoy aquí para ayudarte a encontrar la cepa de cannabis perfecta basada en tus necesidades, preferencias y efectos deseados.',
        quickActions: {
            relaxation: 'Relajación',
            creativity: 'Creatividad',
            sleep: 'Dormir',
            energy: 'Energía',
            painRelief: 'Alivio del Dolor'
        },
        quickMessages: {
            relaxation: "¿Qué es bueno para la relajación?",
            creativity: "Necesito algo para la creatividad",
            sleep: "¿Qué ayuda con el sueño?",
            energy: "Muéstrame cepas energizantes",
            painRelief: "¿Qué es bueno para el alivio del dolor?"
        },
        connected: 'Conectado',
        connecting: 'Conectando...',
        disconnected: 'Desconectado',
        offline: 'Fuera de línea'
    }
};

// Get current language from page
function getChatLang() {
    const lang = document.documentElement.lang || 'es';
    // Extract base language code (e.g., 'es-ES' -> 'es', 'en-US' -> 'en')
    const baseLang = lang.split('-')[0].toLowerCase();
    return CHAT_ERROR_TRANSLATIONS[baseLang] ? baseLang : 'en';
}

// Translation helper for error messages (uses our dictionary)
function t(key, replacements = {}) {
    const lang = getChatLang();
    let text = CHAT_ERROR_TRANSLATIONS[lang][key] || CHAT_ERROR_TRANSLATIONS['en'][key] || key;

    // Replace placeholders like {time}
    Object.keys(replacements).forEach(placeholder => {
        text = text.replace(`{${placeholder}}`, replacements[placeholder]);
    });

    return text;
}

// UI Translation helper for interface texts
function tUI(key) {
    const lang = getChatLang();
    const keys = key.split('.');
    let text = CHAT_UI_TRANSLATIONS[lang];

    for (const k of keys) {
        if (text && text[k]) {
            text = text[k];
        } else {
            // Fallback to English or return key if not found
            text = CHAT_UI_TRANSLATIONS['en'];
            for (const k of keys) {
                if (text && text[k]) {
                    text = text[k];
                } else {
                    return key;
                }
            }
            break;
        }
    }

    return text;
}

// Format seconds into human-readable string (en/es) for rate limit fallback
function formatRetryAfterHuman(seconds) {
    const lang = getChatLang();
    const value = Number(seconds);
    if (!Number.isFinite(value) || value <= 0) {
        return null;
    }

    if (lang === 'es') {
        if (value < 60) {
            return `${value} segundo${value !== 1 ? 's' : ''}`;
        } else if (value < 3600) {
            const minutes = Math.floor(value / 60);
            return `${minutes} minuto${minutes !== 1 ? 's' : ''}`;
        } else {
            const hours = Math.floor(value / 3600);
            const minutes = Math.floor((value % 3600) / 60);
            if (minutes > 0) {
                return `${hours} hora${hours !== 1 ? 's' : ''} y ${minutes} minuto${minutes !== 1 ? 's' : ''}`;
            }
            return `${hours} hora${hours !== 1 ? 's' : ''}`;
        }
    }

    // Default to English
    if (value < 60) {
        return `${value} second${value !== 1 ? 's' : ''}`;
    } else if (value < 3600) {
        const minutes = Math.floor(value / 60);
        return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    } else {
        const hours = Math.floor(value / 3600);
        const minutes = Math.floor((value % 3600) / 60);
        if (minutes > 0) {
            return `${hours} hour${hours !== 1 ? 's' : ''} and ${minutes} minute${minutes !== 1 ? 's' : ''}`;
        }
        return `${hours} hour${hours !== 1 ? 's' : ''}`;
    }
}

// Django gettext wrapper for strain labels (uses Django i18n if available)
function _(text) {
    return (typeof gettext === 'function') ? gettext(text) : text;
}

// Convert basic markdown to HTML (for LLM responses)
function parseMarkdown(str) {
    if (typeof str !== 'string') return '';
    return str
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')  // **bold**
        .replace(/\*(.+?)\*/g, '<em>$1</em>')              // *italic*
        .replace(/\n/g, '<br>');                            // newlines
}

// Sanitize HTML to prevent XSS - strips all tags except safe formatting
function sanitizeHTML(str) {
    if (typeof str !== 'string') return '';
    const temp = document.createElement('div');
    temp.textContent = str;
    return temp.innerHTML;
}

// Sanitize HTML but allow safe formatting tags (for LLM responses)
function sanitizeRichHTML(str) {
    if (typeof str !== 'string') return '';
    const allowedTags = ['b', 'i', 'em', 'strong', 'br', 'p', 'ul', 'ol', 'li', 'h3', 'h4', 'h5'];
    const temp = document.createElement('div');
    temp.innerHTML = str;
    // Remove all script/event handler content
    temp.querySelectorAll('script, iframe, object, embed, form, input, textarea, select, button').forEach(el => el.remove());
    // Remove event handlers from all elements
    temp.querySelectorAll('*').forEach(el => {
        for (const attr of [...el.attributes]) {
            if (attr.name.startsWith('on') || attr.name === 'href' && attr.value.trim().toLowerCase().startsWith('javascript:')) {
                el.removeAttribute(attr.name);
            }
        }
        // Remove disallowed tags but keep their text content
        if (!allowedTags.includes(el.tagName.toLowerCase())) {
            if (!['div', 'span', 'a'].includes(el.tagName.toLowerCase())) {
                el.replaceWith(...el.childNodes);
            }
        }
    });
    // Sanitize remaining <a> tags
    temp.querySelectorAll('a').forEach(a => {
        const href = a.getAttribute('href') || '';
        if (!href.startsWith('http://') && !href.startsWith('https://') && !href.startsWith('/')) {
            a.removeAttribute('href');
        }
        a.setAttribute('rel', 'noopener noreferrer');
        a.setAttribute('target', '_blank');
    });
    return temp.innerHTML;
}

class AIBudtenderChat {
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: options.apiBaseUrl || 'http://localhost:8001',
            apiKey: options.apiKey || '',
            websocketUrl: options.websocketUrl || null, // WebSocket URL for real-time updates
            autoConnect: options.autoConnect !== false,
            maxHistory: options.maxHistory || 10,
            typingDelay: options.typingDelay || 1000,
            retryAttempts: options.retryAttempts || 3,
            retryDelay: options.retryDelay || 2000,
            ...options
        };

        this.isOpen = false;
        this.isConnected = false;
        this.isTyping = false;
        this.sessionTTL = 4 * 60 * 60 * 1000; // 4 hours in ms
        this.checkSessionExpiry();
        this.messageHistory = this.loadHistory();
        this.chatMessages = this.loadChatMessages();
        this.sessionId = this.loadSessionId();
        this.websocket = null;
        this.retryCount = 0;
        this.messageQueue = [];
        
        this.init();
    }

    init() {
        this.createWidget();
        this.bindEvents();
        this.loadWelcomeMessage();
        this.restoreMessages();
        
        if (this.options.autoConnect) {
            this.connectWebSocket();
        }
    }

    createWidget() {
        const widgetHTML = `
            <div class="ai-budtender-chat">
                <div class="connection-status" id="connection-status"></div>
                
                <div class="chat-bubble" id="chat-bubble">
                    <div class="chat-bubble-icon chat-icon"><img src="${this.options.avatarUrl || '/static/img/mascot_avatar_60x60.png'}" alt="" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;"></div>
                    <div class="chat-bubble-icon close-icon">✕</div>
                    <div class="chat-notification-badge" id="notification-badge">1</div>
                </div>
                
                <div class="chat-window" id="chat-window">
                    <div class="chat-header">
                        <div class="chat-header-avatar">🤖</div>
                        <div class="chat-header-info">
                            <h3 id="chat-bot-name">AI Budtender</h3>
                            <p id="chat-bot-role">Cannabis strain expert</p>
                        </div>
                        <div class="chat-status" id="chat-status">Online</div>
                    </div>
                    
                    <div class="chat-messages" id="chat-messages">
                        <div class="welcome-message">
                            <h4 id="chat-welcome-title">Welcome to AI Budtender!</h4>
                            <p id="chat-welcome-message">I'm here to help you find the perfect cannabis strain based on your needs, preferences, and desired effects.</p>
                        </div>
                        
                        <div class="quick-actions" id="quick-actions">
                            <button class="quick-action" data-key="relaxation">Relaxation</button>
                            <button class="quick-action" data-key="creativity">Creativity</button>
                            <button class="quick-action" data-key="sleep">Sleep</button>
                            <button class="quick-action" data-key="energy">Energy</button>
                            <button class="quick-action" data-key="painRelief">Pain Relief</button>
                        </div>
                        
                        <!-- typing indicator is injected dynamically by showTypingIndicator() -->
                    </div>
                    
                    <div class="chat-input-area">
                        <div class="chat-input-container">
                            <textarea
                                id="chat-input"
                                class="chat-input"
                                placeholder="Ask me about cannabis strains..."
                                rows="1"
                                maxlength="2000"
                            ></textarea>
                            <button id="chat-send-button" class="chat-send-button">
                                <span>➤</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', widgetHTML);
        
        // Cache DOM elements
        this.elements = {
            bubble: document.getElementById('chat-bubble'),
            window: document.getElementById('chat-window'),
            messages: document.getElementById('chat-messages'),
            input: document.getElementById('chat-input'),
            sendButton: document.getElementById('chat-send-button'),
            status: document.getElementById('chat-status'),
            connectionStatus: document.getElementById('connection-status'),
            notificationBadge: document.getElementById('notification-badge'),
            quickActions: document.getElementById('quick-actions')
        };

        // Update translations after creating HTML
        this.updateChatTranslations();
    }

    updateChatTranslations() {
        // Update header texts
        const botName = document.getElementById('chat-bot-name');
        const botRole = document.getElementById('chat-bot-role');
        const chatStatus = document.getElementById('chat-status');

        if (botName) botName.textContent = tUI('botName');
        if (botRole) botRole.textContent = tUI('botRole');
        if (chatStatus) chatStatus.textContent = tUI('status');

        // Update welcome message
        const welcomeTitle = document.getElementById('chat-welcome-title');
        const welcomeMessage = document.getElementById('chat-welcome-message');

        if (welcomeTitle) welcomeTitle.textContent = tUI('welcomeTitle');
        if (welcomeMessage) welcomeMessage.textContent = tUI('welcomeMessage');

        // Update quick action buttons
        const quickButtons = document.querySelectorAll('.quick-action[data-key]');
        quickButtons.forEach(button => {
            const key = button.getAttribute('data-key');
            if (key) {
                button.textContent = tUI(`quickActions.${key}`);
                button.setAttribute('data-message', tUI(`quickMessages.${key}`));
            }
        });
    }

    bindEvents() {
        // Toggle chat window
        this.elements.bubble.addEventListener('click', () => this.toggleChat());
        
        // Send message on button click
        this.elements.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter (Shift+Enter for new line)
        this.elements.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea
        this.elements.input.addEventListener('input', () => this.autoResizeTextarea());
        
        // Quick actions
        this.elements.quickActions.addEventListener('click', (e) => {
            if (e.target.classList.contains('quick-action')) {
                const message = e.target.getAttribute('data-message');
                this.sendMessage(message);
            }
        });
        
        // Close chat when clicking outside
        this._onDocumentClick = (e) => {
            if (!e.target.closest('.ai-budtender-chat')) {
                this.closeChat();
            }
        };
        document.addEventListener('click', this._onDocumentClick);

        // Handle page visibility change
        this._onVisibilityChange = () => {
            if (document.visibilityState === 'visible' && !this.isConnected) {
                this.connectWebSocket();
            }
        };
        document.addEventListener('visibilitychange', this._onVisibilityChange);
    }

    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }

    openChat() {
        this.isOpen = true;
        this.elements.bubble.classList.add('active');
        this.elements.window.classList.add('active');
        this.elements.notificationBadge.style.display = 'none';
        this.elements.input.focus();
        
        // Connect WebSocket if not connected
        if (!this.isConnected) {
            this.connectWebSocket();
        }
    }

    closeChat() {
        this.isOpen = false;
        this.elements.bubble.classList.remove('active');
        this.elements.window.classList.remove('active');
    }

    async sendMessage(text = null) {
        const message = text || this.elements.input.value.trim();
        if (!message) return;

        if (!text) {
            this.elements.input.value = '';
            this.autoResizeTextarea();
        }

        this.addMessage('user', message);
        this.showTypingIndicator();
        this.setInputState(false);

        try {
            await this._sendStreaming(message);
        } catch (streamErr) {
            // Streaming failed — fall back to regular blocking API call
            console.warn('Streaming failed, falling back to regular API:', streamErr.message);
            try {
                const response = await this.callAPI(message);
                this.hideTypingIndicator();
                this.handleContextAwareResponse(response);
                this.addMessage('ai', response.response, response.recommended_strains, false, response);
                this.messageHistory.push(message, response.response);
                this.trimHistory();
                this.saveHistory();
            } catch (fallbackErr) {
                console.error('Chat error (fallback):', fallbackErr);
                this.hideTypingIndicator();
                this.addMessage('ai', this.getErrorMessage(fallbackErr), null, true);
            }
        } finally {
            this.setInputState(true);
        }
    }

    /**
     * Primary path: SSE streaming via /api/chat/stream/.
     * Shows strain cards as soon as metadata arrives, then streams text.
     */
    async _sendStreaming(message) {
        const url = '/api/chat/stream/';
        const headers = { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' };
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                          document.querySelector('meta[name=csrf-token]')?.content ||
                          this.getCookie('csrftoken');
        if (csrfToken) headers['X-CSRFToken'] = csrfToken;
        if (this.options.apiKey) headers['Authorization'] = `Bearer ${this.options.apiKey}`;

        const payload = {
            message,
            language: document.documentElement.lang || 'es',
            source_platform: 'cannamente',
        };
        if (this.sessionId) payload.session_id = this.sessionId;

        const fetchResp = await fetch(url, { method: 'POST', headers, body: JSON.stringify(payload) });
        if (!fetchResp.ok) throw new Error(`Stream request failed: ${fetchResp.status}`);

        const reader   = fetchResp.body.getReader();
        const decoder  = new TextDecoder();
        let   buffer   = '';
        let   metadata = null;
        let   streamEl = null;   // The live message bubble DOM element
        let   textNode = null;   // Text node inside the bubble we update
        let   accumText = '';

        const readChunk = async () => {
            // eslint-disable-next-line no-constant-condition
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                const lines = buffer.split('\n');
                buffer = lines.pop(); // keep partial last line

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    let chunk;
                    try { chunk = JSON.parse(line.slice(6)); } catch { continue; }

                    if (chunk.type === 'error') {
                        throw new Error(chunk.message || 'Stream error');
                    }

                    if (chunk.type === 'metadata') {
                        metadata = chunk.data || {};
                        // Store session ID immediately
                        if (metadata.session_id) {
                            this.sessionId = metadata.session_id;
                            this.saveSessionId();
                        }
                        // Replace typing indicator with an empty streaming bubble
                        this.hideTypingIndicator();
                        const created = this._createStreamingBubble(metadata.recommended_strains || []);
                        streamEl  = created.bubble;
                        textNode  = created.textNode;
                        // Scroll to TOP of bubble so text is visible, not the bottom cards
                        streamEl.scrollIntoView({ block: 'start', behavior: 'smooth' });
                    }

                    if (chunk.type === 'response_chunk' && chunk.text) {
                        accumText += chunk.text;
                        if (textNode) textNode.textContent = accumText;
                        // Follow the cursor (text area), not the bottom of cards
                        if (textNode) textNode.scrollIntoView({ block: 'nearest', behavior: 'instant' });
                    }

                    if (chunk.type === 'done') {
                        this._finalizeStreamingBubble(streamEl, textNode, accumText, metadata);
                        this.messageHistory.push(message, accumText);
                        this.trimHistory();
                        this.saveHistory();
                        return; // Stream finished
                    }
                }
            }
            // Reader ended without 'done' — finalise anyway
            if (streamEl) this._finalizeStreamingBubble(streamEl, textNode, accumText, metadata);
            if (accumText) { this.messageHistory.push(message, accumText); this.trimHistory(); this.saveHistory(); }
        };

        await readChunk();
    }

    /** Create an AI bubble with a blinking cursor. Returns {bubble, textNode}. */
    _createStreamingBubble(strains) {
        const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

        let strainsHTML = '';
        if (strains && strains.length > 0) {
            strainsHTML = `<div class="strain-recommendations">${strains.map(s => this.createStrainCard(s)).join('')}</div>`;
        }

        const bubble = document.createElement('div');
        bubble.className = 'message ai';
        bubble.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content streaming" id="stream-content">
                <span class="stream-text"></span><span class="streaming-cursor"></span>
                ${strainsHTML}
                <div class="message-time">${time}</div>
            </div>`;

        this.elements.messages.appendChild(bubble);

        // Get the text span so we can update it efficiently
        const textSpan = bubble.querySelector('.stream-text');
        // We'll update textSpan.textContent rather than a raw text node
        return { bubble, textNode: textSpan };
    }

    /** Remove cursor, run context-aware hooks, persist to chatMessages. */
    _finalizeStreamingBubble(bubble, _textSpan, finalText, metadata) {
        if (!bubble) return;
        // Remove blinking cursor
        const cursor = bubble.querySelector('.streaming-cursor');
        if (cursor) cursor.remove();
        // Mark content as no longer streaming
        const content = bubble.querySelector('.message-content');
        if (content) content.classList.remove('streaming');

        // Convert accumulated markdown to HTML in the stream-text span
        const textSpan = bubble.querySelector('.stream-text');
        if (textSpan && finalText) {
            textSpan.innerHTML = sanitizeRichHTML(parseMarkdown(finalText));
        }

        // Context-aware post-processing (quick actions, indicators)
        if (metadata) this.handleContextAwareResponse(metadata);

        // Save to persistent chat history
        const messageData = {
            type: 'ai',
            content: finalText,
            strains: metadata?.recommended_strains || null,
            isError: false,
            timestamp: Date.now(),
            contextData: metadata,
        };
        this.chatMessages.push(messageData);
        this.saveChatMessages();

        if (metadata) this.handleContextAwareMessage(metadata);
        if (!this.isOpen) this.showNotification();
        this.scrollToBottom();
    }

    async callAPI(message) {
        const url = `/api/chat/chat/`;  // Django endpoint, not canagent
        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };
        
        // Add CSRF token for Django
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                         document.querySelector('meta[name=csrf-token]')?.content ||
                         this.getCookie('csrftoken');
        
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        // Add API key if provided
        if (this.options.apiKey) {
            headers['Authorization'] = `Bearer ${this.options.apiKey}`;
        }
        
        const payload = {
            message: message,
            history: this.getRecentHistory(),
            language: document.documentElement.lang || 'es'  // Current page language
        };
        
        // Context-Aware Architecture v2.0 - Add session_id and source_platform
        if (this.sessionId) {
            payload.session_id = this.sessionId;
            console.log('🔄 Sending session_id:', this.sessionId);
        } else {
            console.log('⚠️ No session_id found, creating new session');
        }
        payload.source_platform = 'cannamente';  // Platform identification
        
        const response = await fetch(url, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            // Try to parse error response for details (e.g., rate limit info)
            let errorData = null;
            try {
                errorData = await response.json();
            } catch (e) {
                // Response body is not JSON
            }

            const error = new Error(`API request failed: ${response.status} ${response.statusText}`);
            error.status = response.status;
            error.data = errorData;
            const retryAfterHeader = response.headers.get('Retry-After');
            error.retryAfterSeconds = retryAfterHeader ? parseInt(retryAfterHeader, 10) : null;
            throw error;
        }

        const data = await response.json();
        
        // Store session ID for future requests
        if (data.session_id) {
            console.log('✅ Received session_id:', data.session_id);
            this.sessionId = data.session_id;
            this.saveSessionId();
        } else {
            console.log('❌ No session_id in response');
        }
        
        return data;
    }

    addMessage(type, content, strains = null, isError = false, contextData = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const avatar = type === 'user' ? '👤' : '🤖';
        const time = new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });

        // Sanitize content: escape user messages, parse markdown + allow safe HTML in AI responses
        const safeContent = type === 'user' ? sanitizeHTML(content) : sanitizeRichHTML(parseMarkdown(content));

        let strainsHTML = '';
        if (strains && strains.length > 0) {
            strainsHTML = `
                <div class="strain-recommendations">
                    ${strains.map(strain => this.createStrainCard(strain)).join('')}
                </div>
            `;
        }

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content ${isError ? 'error-message' : ''}">
                ${safeContent}
                ${strainsHTML}
                <div class="message-time">${time}</div>
            </div>
        `;
        
        this.elements.messages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Context-Aware Architecture v2.0 - Save enhanced message data
        const messageData = {
            type: type,
            content: content,
            strains: strains,
            isError: isError,
            timestamp: Date.now(),
            contextData: contextData  // Store context-aware metadata
        };
        this.chatMessages.push(messageData);
        this.saveChatMessages();
        
        // Handle context-aware features for AI messages
        if (type === 'ai' && contextData) {
            this.handleContextAwareMessage(contextData);
        }
        
        // Show notification if chat is closed
        if (!this.isOpen && type === 'ai') {
            this.showNotification();
        }
    }

    createStrainCard(strain) {
        const categoryClass = strain.category ? strain.category.toLowerCase().replace(/[^a-z]/g, '') : 'hybrid';

        // Handle cannabinoids - API returns strings like "18.50", "0.10" or null
        const thcValue = strain.thc ? parseFloat(strain.thc).toFixed(0) : 'N/A';
        const cbdValue = strain.cbd ? parseFloat(strain.cbd).toFixed(1) : null;
        const cbgValue = strain.cbg ? parseFloat(strain.cbg).toFixed(1) : null;

        // Determine secondary cannabinoid display logic
        let secondaryCannabinoid = '';
        const cbdFloat = strain.cbd ? parseFloat(strain.cbd) : 0;
        const cbgFloat = strain.cbg ? parseFloat(strain.cbg) : 0;

        if (cbgFloat > 0 && cbdFloat < 1) {
            secondaryCannabinoid = `
                <div class="strain-detail">
                    <div class="strain-detail-label">CBG</div>
                    <div class="strain-detail-value">${cbgValue}%</div>
                </div>`;
        } else if (cbdFloat > 0) {
            secondaryCannabinoid = `
                <div class="strain-detail">
                    <div class="strain-detail-label">CBD</div>
                    <div class="strain-detail-value">${cbdValue}%</div>
                </div>`;
        }

        // Sanitize all text fields from API response
        const safeName = sanitizeHTML(strain.name || '');
        const safeCategory = sanitizeHTML(strain.category || 'Hybrid');

        // Validate URL - only allow safe URLs
        let safeUrl = '#';
        if (strain.url && (strain.url.startsWith('/') || strain.url.startsWith('https://'))) {
            safeUrl = sanitizeHTML(strain.url);
        }

        // Build effects summary (first 3 feelings) - sanitized
        let effectsSummary = '';
        if (strain.feelings && strain.feelings.length > 0) {
            const topEffects = strain.feelings.slice(0, 3)
                .map(f => sanitizeHTML(f.name))
                .join(', ');
            effectsSummary = `<div class="strain-effects"><span class="strain-label">${_('Efectos')}:</span> ${topEffects}</div>`;
        }

        // Medical uses summary (first 2 conditions) - sanitized
        let medicalSummary = '';
        if (strain.helps_with && strain.helps_with.length > 0) {
            const conditions = strain.helps_with.slice(0, 2)
                .map(h => sanitizeHTML(h.name))
                .join(', ');
            medicalSummary = `<div class="strain-medical"><span class="strain-label">${_('Ayuda con')}:</span> ${conditions}</div>`;
        }

        // Flavor notes (first 2 flavors) - sanitized
        let flavorSummary = '';
        if (strain.flavors && strain.flavors.length > 0) {
            const flavors = strain.flavors.slice(0, 2)
                .map(f => sanitizeHTML(f.name))
                .join(', ');
            flavorSummary = `<div class="strain-flavors"><span class="strain-label">${_('Sabores')}:</span> ${flavors}</div>`;
        }

        return `
            <div class="strain-card" onclick="window.open('${safeUrl}', '_blank')">
                <div class="strain-card-header">
                    <div class="strain-name">${safeName}</div>
                    <div class="strain-category ${categoryClass}">${safeCategory}</div>
                </div>
                <div class="strain-details">
                    <div class="strain-detail">
                        <div class="strain-detail-label">THC</div>
                        <div class="strain-detail-value">${thcValue}%</div>
                    </div>
                    ${secondaryCannabinoid}
                </div>
                ${effectsSummary}
                ${medicalSummary}
                ${flavorSummary}
            </div>
        `;
    }

    showTypingIndicator() {
        if (this.isTyping) return;

        this.isTyping = true;

        const typingDiv = document.createElement('div');
        typingDiv.className = 'message ai typing-message';
        typingDiv.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;

        this.elements.messages.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.isTyping = false;
        const typingDiv = this.elements.messages.querySelector('.typing-message');
        if (typingDiv) {
            typingDiv.remove();
        }
    }

    setInputState(enabled) {
        this.elements.input.disabled = !enabled;
        this.elements.sendButton.disabled = !enabled;
        
        if (enabled) {
            this.elements.input.focus();
        }
    }

    showNotification() {
        this.elements.notificationBadge.style.display = 'flex';
    }

    autoResizeTextarea() {
        const textarea = this.elements.input;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
    }

    scrollToBottom() {
        this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
    }

    getRecentHistory() {
        return this.messageHistory.slice(-this.options.maxHistory);
    }

    trimHistory() {
        if (this.messageHistory.length > this.options.maxHistory * 2) {
            this.messageHistory = this.messageHistory.slice(-this.options.maxHistory);
        }
    }

    clearStoredSessionData() {
        localStorage.removeItem('ai-budtender-messages');
        localStorage.removeItem('ai-budtender-history');
        localStorage.removeItem('ai-budtender-session-id');
        localStorage.removeItem('ai-budtender-session-start');
    }

    hasPersistedSessionData() {
        return Boolean(
            localStorage.getItem('ai-budtender-messages') ||
            localStorage.getItem('ai-budtender-history') ||
            localStorage.getItem('ai-budtender-session-id')
        );
    }

    resolveSessionStartTimestamp() {
        const rawStart = localStorage.getItem('ai-budtender-session-start');
        const parsedStart = Number.parseInt(rawStart || '', 10);
        if (Number.isFinite(parsedStart) && parsedStart > 0) {
            return parsedStart;
        }

        const savedMessages = localStorage.getItem('ai-budtender-messages');
        if (!savedMessages) {
            return null;
        }

        let parsedMessages = null;
        try {
            parsedMessages = JSON.parse(savedMessages);
        } catch (error) {
            return null;
        }

        if (!Array.isArray(parsedMessages) || parsedMessages.length === 0) {
            return null;
        }

        const timestamps = parsedMessages
            .map((message) => Number(message?.timestamp))
            .filter((ts) => Number.isFinite(ts) && ts > 0);

        if (timestamps.length === 0) {
            return null;
        }

        const inferredStart = Math.min(...timestamps);
        localStorage.setItem('ai-budtender-session-start', String(inferredStart));
        return inferredStart;
    }

    loadHistory() {
        try {
            const saved = localStorage.getItem('ai-budtender-history');
            if (!saved) return [];

            const parsed = JSON.parse(saved);
            return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
            console.warn('Failed to load chat history:', error);
            return [];
        }
    }

    saveHistory() {
        try {
            localStorage.setItem('ai-budtender-history', JSON.stringify(this.messageHistory));
        } catch (error) {
            console.warn('Failed to save chat history:', error);
        }
    }

    loadChatMessages() {
        try {
            const saved = localStorage.getItem('ai-budtender-messages');
            if (!saved) return [];

            const parsed = JSON.parse(saved);
            return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
            console.warn('Failed to load chat messages:', error);
            return [];
        }
    }

    saveChatMessages() {
        try {
            if (this.chatMessages.length > 50) {
                this.chatMessages = this.chatMessages.slice(-50);
            }
            const rawStart = localStorage.getItem('ai-budtender-session-start');
            const parsedStart = Number.parseInt(rawStart || '', 10);
            if (!Number.isFinite(parsedStart) || parsedStart <= 0) {
                const firstMessageTs = Number(this.chatMessages[0]?.timestamp);
                const startTs = Number.isFinite(firstMessageTs) && firstMessageTs > 0
                    ? firstMessageTs
                    : Date.now();
                localStorage.setItem('ai-budtender-session-start', String(startTs));
            }
            localStorage.setItem('ai-budtender-messages', JSON.stringify(this.chatMessages));
        } catch (error) {
            console.warn('Failed to save chat messages:', error);
        }
    }

    loadSessionId() {
        try {
            return localStorage.getItem('ai-budtender-session-id') || null;
        } catch (error) {
            console.warn('Failed to load session ID:', error);
            return null;
        }
    }

    saveSessionId() {
        try {
            if (this.sessionId) {
                localStorage.setItem('ai-budtender-session-id', this.sessionId);
            }
        } catch (error) {
            console.warn('Failed to save session ID:', error);
        }
    }

    checkSessionExpiry() {
        try {
            const startTimestamp = this.resolveSessionStartTimestamp();

            // If we have persisted data but no valid timestamp, data is stale/legacy: clear it.
            if (!startTimestamp) {
                if (this.hasPersistedSessionData()) {
                    this.clearStoredSessionData();
                }
                return;
            }

            const sessionAge = Date.now() - startTimestamp;
            const maxFutureSkew = 5 * 60 * 1000; // tolerate minor client clock drift
            if (sessionAge > this.sessionTTL || sessionAge < -maxFutureSkew) {
                this.clearStoredSessionData();
            }
        } catch (error) {
            console.warn('Failed to check session expiry:', error);
        }
    }

    loadWelcomeMessage() {
        // Hide quick actions after first interaction
        const hasHistory = this.messageHistory.length > 0;
        if (hasHistory) {
            this.elements.quickActions.style.display = 'none';
        }
    }

    restoreMessages() {
        // Restore saved messages from localStorage
        if (this.chatMessages.length > 0) {
            // Hide quick actions since we have history
            this.elements.quickActions.style.display = 'none';
            
            // Restore each message with context data
            this.chatMessages.forEach(messageData => {
                this.addMessageToDOM(
                    messageData.type, 
                    messageData.content, 
                    messageData.strains, 
                    messageData.isError,
                    messageData.contextData
                );
            });
        }
    }

    addMessageToDOM(type, content, strains = null, isError = false, contextData = null) {
        // Same as addMessage but without saving to localStorage (to avoid duplication)
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const avatar = type === 'user' ? '👤' : '🤖';
        const time = new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });

        const safeContent = type === 'user' ? sanitizeHTML(content) : sanitizeRichHTML(parseMarkdown(content));

        let strainsHTML = '';
        if (strains && strains.length > 0) {
            strainsHTML = `
                <div class="strain-recommendations">
                    ${strains.map(strain => this.createStrainCard(strain)).join('')}
                </div>
            `;
        }

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content ${isError ? 'error-message' : ''}">
                ${safeContent}
                ${strainsHTML}
                <div class="message-time">${time}</div>
            </div>
        `;
        
        this.elements.messages.appendChild(messageDiv);
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    getErrorMessage(error) {
        if (error.message.includes('Failed to fetch')) {
            return t('connectionError');
        } else if (error.status === 429 || error.message.includes('429')) {
            // Rate limit exceeded - show retry time if available
            if (error.data && error.data.retry_after_seconds) {
                const human = formatRetryAfterHuman(error.data.retry_after_seconds);
                if (human) {
                    return t('rateLimitExceeded', { time: human });
                }
            }
            if (error.retryAfterSeconds) {
                const human = formatRetryAfterHuman(error.retryAfterSeconds);
                if (human) {
                    return t('rateLimitExceeded', { time: human });
                }
            }
            if (error.data && error.data.retry_after_human) {
                return t('rateLimitExceeded', { time: error.data.retry_after_human });
            }
            return t('rateLimitGeneric');
        } else if (error.status === 503 || error.message.includes('503')) {
            // Service disabled
            if (error.data && error.data.error) {
                return error.data.error;
            }
            return t('serviceUnavailable');
        } else if (error.message.includes('500')) {
            return t('serverError');
        } else {
            return t('genericError');
        }
    }

    // WebSocket Implementation for Real-time Updates
    connectWebSocket() {
        if (!this.options.websocketUrl) {
            this.updateConnectionStatus('connected');
            return;
        }

        this.updateConnectionStatus('connecting');
        
        try {
            this.websocket = new WebSocket(this.options.websocketUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.retryCount = 0;
                this.updateConnectionStatus('connected');
                this.processMessageQueue();
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus('disconnected');
                this.scheduleReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.isConnected = false;
                this.updateConnectionStatus('disconnected');
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.updateConnectionStatus('disconnected');
            this.scheduleReconnect();
        }
    }

    handleWebSocketMessage(data) {
        // Handle real-time messages from WebSocket
        switch (data.type) {
            case 'response':
                this.addMessage('ai', data.response, data.recommended_strains);
                break;
            case 'typing':
                if (data.typing) {
                    this.showTypingIndicator();
                } else {
                    this.hideTypingIndicator();
                }
                break;
            case 'error':
                this.addMessage('ai', this.getErrorMessage(new Error(data.message)), null, true);
                break;
            default:
                console.warn('Unknown WebSocket message type:', data.type);
        }
    }

    scheduleReconnect() {
        if (this.retryCount >= this.options.retryAttempts) {
            console.log('Max reconnection attempts reached');
            return;
        }
        
        this.retryCount++;
        const delay = this.options.retryDelay * Math.pow(2, this.retryCount - 1); // Exponential backoff
        
        console.log(`Scheduling reconnect attempt ${this.retryCount} in ${delay}ms`);
        setTimeout(() => {
            if (!this.isConnected) {
                this.connectWebSocket();
            }
        }, delay);
    }

    processMessageQueue() {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.websocket.send(JSON.stringify(message));
        }
    }

    updateConnectionStatus(status) {
        const statusElement = this.elements.connectionStatus;
        const chatStatus = this.elements.status;
        
        statusElement.className = `connection-status ${status}`;
        
        switch (status) {
            case 'connected':
                statusElement.textContent = tUI('connected');
                chatStatus.textContent = tUI('status');
                break;
            case 'connecting':
                statusElement.textContent = tUI('connecting');
                chatStatus.textContent = tUI('connecting');
                break;
            case 'disconnected':
                statusElement.textContent = tUI('disconnected');
                chatStatus.textContent = tUI('offline');
                break;
        }
        
        // Show status briefly
        statusElement.classList.add('show');
        setTimeout(() => {
            statusElement.classList.remove('show');
        }, 3000);
    }

    // Context-Aware Architecture v2.0 Methods
    handleContextAwareResponse(response) {
        // Update quick actions based on context
        if (response.quick_actions && response.quick_actions.length > 0) {
            this.updateQuickActions(response.quick_actions);
        }

        // Show session status indicators
        if (response.is_restored) {
            this.showSessionIndicator(t('sessionRestored'), 'info');
        }

        if (response.is_fallback) {
            this.showSessionIndicator(t('basicMode'), 'warning');
        }

        // Show warnings if any
        if (response.warnings && response.warnings.length > 0) {
            this.showSessionIndicator(`${t('conflictsResolved')}: ${response.warnings.length}`, 'warning');
        }

        // Show confidence if low
        if (response.confidence && response.confidence < 0.7) {
            const confidencePercent = Math.round(response.confidence * 100);
            this.showSessionIndicator(`${t('confidence')}: ${confidencePercent}%`, 'caution');
        }
    }

    handleContextAwareMessage(contextData) {
        // Handle different query types for better UX
        switch (contextData.query_type) {
            case 'follow_up':
                this.updateChatHeader(t('followUpQuestion'));
                break;
            case 'comparison':
                this.updateChatHeader(t('comparingOptions'));
                break;
            case 'clarification':
                this.updateChatHeader(t('clarifyingDoubts'));
                break;
            case 'reset':
                this.updateChatHeader(t('newSearch'));
                this.clearContextualState();
                break;
            default:
                this.updateChatHeader(tUI('botName'));
        }
    }
    
    updateQuickActions(actions) {
        // Update quick actions with contextual suggestions
        const quickActionsContainer = this.elements.quickActions;
        if (!actions || actions.length === 0) {
            quickActionsContainer.style.display = 'none';
            return;
        }
        
        quickActionsContainer.innerHTML = '';
        actions.forEach(action => {
            const button = document.createElement('button');
            button.className = 'quick-action';
            button.setAttribute('data-message', action);
            button.textContent = action;
            quickActionsContainer.appendChild(button);
        });
        
        quickActionsContainer.style.display = 'flex';
    }
    
    showSessionIndicator(message, type = 'info') {
        // Show temporary status indicator
        const indicator = document.createElement('div');
        indicator.className = `session-indicator ${type}`;
        indicator.textContent = message;
        
        this.elements.messages.appendChild(indicator);
        this.scrollToBottom();
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }, 5000);
    }
    
    updateChatHeader(subtitle) {
        const headerInfo = this.elements.window.querySelector('.chat-header-info p');
        if (headerInfo) {
            headerInfo.textContent = subtitle;
        }
    }
    
    clearContextualState() {
        // Clear quick actions when starting new search
        this.elements.quickActions.style.display = 'none';
        this.updateChatHeader(tUI('botRole'));
    }
    
    resetConversation() {
        // Send reset command to start fresh conversation
        this.sendMessage('Empezar nueva búsqueda');
    }

    // Public API methods
    destroy() {
        if (this.websocket) {
            this.websocket.close();
        }

        document.removeEventListener('click', this._onDocumentClick);
        document.removeEventListener('visibilitychange', this._onVisibilityChange);

        const widget = document.querySelector('.ai-budtender-chat');
        if (widget) {
            widget.remove();
        }

        this.elements = null;
    }

    clearHistory() {
        this.messageHistory = [];
        this.chatMessages = [];
        this.sessionId = null;

        this.clearStoredSessionData();
        
        // Clear displayed messages except welcome
        const messages = this.elements.messages.querySelectorAll('.message:not(.welcome-message)');
        messages.forEach(msg => msg.remove());
        
        // Show quick actions again
        this.elements.quickActions.style.display = 'flex';
    }

    sendCustomMessage(message) {
        this.sendMessage(message);
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Check if widget should be initialized
    const shouldInit = document.querySelector('[data-ai-budtender-chat]') || 
                      window.AIBudtenderChatConfig;
    
    if (shouldInit) {
        const config = window.AIBudtenderChatConfig || {};
        window.aiBudtenderChat = new AIBudtenderChat(config);
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AIBudtenderChat;
}
