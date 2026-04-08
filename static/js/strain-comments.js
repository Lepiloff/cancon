(function() {
    'use strict';

    var cfg = window.StrainCommentsConfig || {};
    var form = document.getElementById('strain-comment-form');
    var list = document.getElementById('strain-comments-list');
    var emptyState = document.getElementById('strain-comments-empty');
    var moreButton = document.getElementById('strain-comments-more');
    var errorNode = document.getElementById('strain-comment-form-error');
    var noticeNode = document.getElementById('strain-comment-form-notice');
    var countNode = document.querySelector('[data-comments-count]');

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

    function setMessage(node, text) {
        if (!node) {
            return;
        }
        if (!text) {
            node.hidden = true;
            node.textContent = '';
            return;
        }
        node.hidden = false;
        node.textContent = text;
    }

    function updateEmptyState() {
        if (!emptyState || !list) {
            return;
        }
        emptyState.classList.toggle('sd-comments-empty--hidden', !!list.children.length);
    }

    function incrementCountIfNeeded(commentId) {
        if (!countNode || !commentId) {
            return;
        }
        if (list.querySelector('[data-comment-id="' + commentId + '"]')) {
            return;
        }
        countNode.textContent = String((parseInt(countNode.textContent || '0', 10) || 0) + 1);
    }

    function removeComment(commentId) {
        if (!list || !commentId) {
            return;
        }

        var existing = list.querySelector('[data-comment-id="' + commentId + '"]');
        if (!existing) {
            return;
        }

        existing.remove();
        if (countNode) {
            countNode.textContent = String(Math.max((parseInt(countNode.textContent || '0', 10) || 0) - 1, 0));
        }
        updateEmptyState();
    }

    function upsertComment(html, commentId) {
        if (!html || !list) {
            return;
        }

        var wrapper = document.createElement('div');
        wrapper.innerHTML = html.trim();
        var newNode = wrapper.firstElementChild;
        if (!newNode) {
            return;
        }

        var existing = commentId ? list.querySelector('[data-comment-id="' + commentId + '"]') : null;
        if (existing) {
            existing.replaceWith(newNode);
        } else {
            incrementCountIfNeeded(commentId);
            list.insertBefore(newNode, list.firstChild);
        }

        updateEmptyState();
    }

    function submitComment(event) {
        event.preventDefault();
        setMessage(errorNode, '');
        setMessage(noticeNode, '');

        var pros = (form.elements.pros.value || '').trim();
        var cons = (form.elements.cons.value || '').trim();
        var reactionField = form.querySelector('input[name="reaction"]:checked');

        if (!pros && !cons) {
            setMessage(errorNode, cfg.emptyError || '');
            return;
        }

        if (!reactionField) {
            setMessage(errorNode, cfg.genericError || '');
            return;
        }

        fetch(cfg.submitUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || '',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                strain_id: cfg.strainId,
                pros: pros,
                cons: cons,
                reaction: reactionField.value
            })
        })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Comment submit failed');
                }
                return response.json();
            })
            .then(function(payload) {
                if (payload.status === 'approved' && payload.html) {
                    upsertComment(payload.html, payload.comment_id);
                    setMessage(noticeNode, cfg.approvedMessage || '');
                } else if (payload.status === 'pending') {
                    removeComment(payload.comment_id);
                    setMessage(noticeNode, cfg.pendingMessage || '');
                } else if (payload.status === 'rejected') {
                    removeComment(payload.comment_id);
                    setMessage(noticeNode, cfg.rejectedMessage || '');
                } else {
                    setMessage(noticeNode, cfg.genericError || '');
                }
            })
            .catch(function() {
                setMessage(errorNode, cfg.genericError || '');
            });
    }

    function loadMoreComments() {
        var nextPage = moreButton ? moreButton.getAttribute('data-next-page') : null;
        if (!nextPage) {
            return;
        }

        fetch(cfg.listUrl + '?strain_id=' + encodeURIComponent(cfg.strainId) + '&page=' + encodeURIComponent(nextPage), {
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Comment list failed');
                }
                return response.json();
            })
            .then(function(payload) {
                if (payload.html) {
                    var wrapper = document.createElement('div');
                    wrapper.innerHTML = payload.html;
                    while (wrapper.firstChild) {
                        list.appendChild(wrapper.firstChild);
                    }
                }

                updateEmptyState();

                if (payload.has_more && payload.next_page) {
                    moreButton.setAttribute('data-next-page', payload.next_page);
                } else {
                    moreButton.remove();
                }
            })
            .catch(function() {
                setMessage(errorNode, cfg.genericError || '');
            });
    }

    if (form && cfg.isAuthenticated) {
        form.addEventListener('submit', submitComment);
    }

    if (moreButton) {
        moreButton.addEventListener('click', loadMoreComments);
    }

    updateEmptyState();
})();
