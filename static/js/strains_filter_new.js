(function() {
    'use strict';

    // --- URL Params ---
    function getParams() {
        return new URLSearchParams(window.location.search);
    }

    function navigateWithParams(params) {
        params.delete('page');
        var url = window.location.protocol + '//' + window.location.host +
                  window.location.pathname + '?' + params.toString();
        window.location.href = url;
    }

    // --- Chip Management ---
    var chipContainer;

    function createChip(name, value, label) {
        var chip = document.createElement('div');
        chip.className = 'sf-chip';
        chip.setAttribute('data-name', name);
        chip.setAttribute('data-value', value);

        var text = document.createElement('span');
        text.textContent = label;
        chip.appendChild(text);

        var remove = document.createElement('span');
        remove.className = 'sf-chip__remove';
        remove.innerHTML = '<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="2" y1="2" x2="8" y2="8"/><line x1="8" y1="2" x2="2" y2="8"/></svg>';
        remove.addEventListener('click', function() {
            removeFilter(name, value);
        });
        chip.appendChild(remove);

        chipContainer.appendChild(chip);
    }

    function removeChip(name, value) {
        var chips = chipContainer.querySelectorAll('.sf-chip');
        for (var i = 0; i < chips.length; i++) {
            if (chips[i].getAttribute('data-name') === name &&
                chips[i].getAttribute('data-value') === value) {
                chips[i].remove();
                break;
            }
        }
    }

    function removeChipsByName(name) {
        var chips = chipContainer.querySelectorAll('.sf-chip[data-name="' + name + '"]');
        for (var i = 0; i < chips.length; i++) {
            chips[i].remove();
        }
    }

    function removeFilter(name, value) {
        // For THC segments, special handling
        if (name === 'thc') {
            removeTHCFilter(value);
            return;
        }

        // Uncheck the checkbox
        var input = document.querySelector(
            '#filterForm input[name="' + name + '"][value="' + value + '"]'
        );
        if (input) input.checked = false;

        // Update URL and navigate
        var params = getParams();
        var values = (params.get(name) || '').split(',').filter(function(v) { return v && v !== value; });
        if (values.length === 0) {
            params.delete(name);
        } else {
            params.set(name, values.join(','));
        }
        navigateWithParams(params);
    }

    function removeTHCFilter(value) {
        // Uncheck hidden THC checkbox
        var input = document.querySelector(
            '#filterForm input[name="thc"][value="' + value + '"]'
        );
        if (input) input.checked = false;

        // Deactivate corresponding segment button
        var seg = document.querySelector('.sf-seg[data-thc="' + value + '"]');
        if (seg) seg.classList.remove('is-active');

        var params = getParams();
        var values = (params.get('thc') || '').split(',').filter(function(v) { return v && v !== value; });
        if (values.length === 0) {
            params.delete('thc');
        } else {
            params.set('thc', values.join(','));
        }
        navigateWithParams(params);
    }

    // --- Reset All ---
    function updateResetVisibility() {
        var resetBtn = document.querySelector('.sf-reset');
        if (!resetBtn) return;
        var hasChips = chipContainer && chipContainer.children.length > 0;
        resetBtn.classList.toggle('is-visible', hasChips);
    }

    function resetAll() {
        var form = document.getElementById('filterForm');
        var inputs = form.querySelectorAll('input[type="checkbox"]');
        for (var i = 0; i < inputs.length; i++) {
            inputs[i].checked = false;
        }
        resetSegments();
        window.location.href = window.location.pathname;
    }

    // --- Dropdown Toggle ---
    function closeAllDropdowns() {
        var dropdowns = document.querySelectorAll('.sf-dropdown, .sf-thc');
        var btns = document.querySelectorAll('.sf-btn');
        for (var i = 0; i < dropdowns.length; i++) {
            dropdowns[i].classList.remove('is-open');
        }
        for (var j = 0; j < btns.length; j++) {
            btns[j].classList.remove('is-open');
        }
        var backdrop = document.querySelector('.sf-backdrop');
        if (backdrop) backdrop.classList.remove('is-visible');
    }

    function toggleDropdown(btn) {
        var group = btn.closest('.sf-group');
        var dropdown = group.querySelector('.sf-dropdown, .sf-thc');
        var isOpen = dropdown.classList.contains('is-open');

        closeAllDropdowns();

        if (!isOpen) {
            dropdown.classList.add('is-open');
            btn.classList.add('is-open');
            var backdrop = document.querySelector('.sf-backdrop');
            if (backdrop) backdrop.classList.add('is-visible');
        }
    }

    // --- Checkbox change handler ---
    function onCheckboxChange(e) {
        var input = e.target;
        var name = input.name;
        var value = input.value;
        var params = getParams();

        if (input.checked) {
            var existing = params.get(name);
            if (existing) {
                params.set(name, existing + ',' + value);
            } else {
                params.set(name, value);
            }
            var label = input.closest('.sf-check').querySelector('.sf-check__label').textContent.trim();
            createChip(name, value, label);
        } else {
            var vals = (params.get(name) || '').split(',').filter(function(v) { return v !== value; });
            if (vals.length === 0) {
                params.delete(name);
            } else {
                params.set(name, vals.join(','));
            }
            removeChip(name, value);
        }

        navigateWithParams(params);
    }

    // --- THC Segment Buttons ---
    function resetSegments() {
        var segs = document.querySelectorAll('.sf-seg');
        for (var i = 0; i < segs.length; i++) {
            segs[i].classList.remove('is-active');
        }
        var thcInputs = document.querySelectorAll('#filterForm input[name="thc"]');
        for (var j = 0; j < thcInputs.length; j++) {
            thcInputs[j].checked = false;
        }
    }

    function onSegmentClick(e) {
        var seg = e.currentTarget;
        var thcValue = seg.getAttribute('data-thc');
        var isActive = seg.classList.contains('is-active');

        // Toggle this segment
        seg.classList.toggle('is-active');

        // Sync hidden checkbox
        var hiddenInput = document.querySelector('#filterForm input[name="thc"][value="' + thcValue + '"]');
        if (hiddenInput) hiddenInput.checked = !isActive;

        // Collect all active THC values
        var activeSegs = document.querySelectorAll('.sf-seg.is-active');
        var thcValues = [];
        for (var i = 0; i < activeSegs.length; i++) {
            thcValues.push(activeSegs[i].getAttribute('data-thc'));
        }

        // Update chips
        removeChipsByName('thc');
        for (var k = 0; k < thcValues.length; k++) {
            var segEl = document.querySelector('.sf-seg[data-thc="' + thcValues[k] + '"]');
            var labelText = segEl ? segEl.textContent.trim() : thcValues[k];
            createChip('thc', thcValues[k], 'THC: ' + labelText);
        }

        // Navigate
        var params = getParams();
        if (thcValues.length > 0) {
            params.set('thc', thcValues.join(','));
        } else {
            params.delete('thc');
        }
        navigateWithParams(params);
    }

    function initSegments() {
        var segs = document.querySelectorAll('.sf-seg');
        if (!segs.length) return;

        // Attach click handlers
        for (var i = 0; i < segs.length; i++) {
            segs[i].addEventListener('click', onSegmentClick);
        }

        // Initialize from URL params
        var params = getParams();
        var thcParam = params.get('thc');
        if (thcParam) {
            var thcVals = thcParam.split(',');
            for (var j = 0; j < thcVals.length; j++) {
                var seg = document.querySelector('.sf-seg[data-thc="' + thcVals[j] + '"]');
                if (seg) seg.classList.add('is-active');

                var hiddenInput = document.querySelector('#filterForm input[name="thc"][value="' + thcVals[j] + '"]');
                if (hiddenInput) hiddenInput.checked = true;

                var labelText = seg ? seg.textContent.trim() : thcVals[j];
                createChip('thc', thcVals[j], 'THC: ' + labelText);
            }
        }
    }

    // --- Button active state ---
    function updateButtonStates() {
        var groups = document.querySelectorAll('.sf-group');
        for (var i = 0; i < groups.length; i++) {
            var btn = groups[i].querySelector('.sf-btn');
            var hasThc = groups[i].querySelector('.sf-thc');
            var isActive;

            if (hasThc) {
                // For THC group, check for active segment buttons
                isActive = groups[i].querySelectorAll('.sf-seg.is-active').length > 0;
            } else {
                isActive = groups[i].querySelectorAll('input[type="checkbox"]:checked').length > 0;
            }

            btn.classList.toggle('has-active', isActive);
        }
    }

    // --- Init ---
    document.addEventListener('DOMContentLoaded', function() {
        chipContainer = document.querySelector('.sf-chips');
        if (!chipContainer) return;

        // Dropdown toggle
        var btns = document.querySelectorAll('.sf-btn');
        for (var i = 0; i < btns.length; i++) {
            btns[i].addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                toggleDropdown(this);
            });
        }

        // Close on outside click
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.sf-group')) {
                closeAllDropdowns();
            }
        });

        // Backdrop close
        var backdrop = document.querySelector('.sf-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', closeAllDropdowns);
        }

        // Checkbox change handlers
        var checkboxes = document.querySelectorAll('.sf-check input[type="checkbox"]');
        for (var j = 0; j < checkboxes.length; j++) {
            checkboxes[j].addEventListener('change', onCheckboxChange);
        }

        // Initialize checkboxes from URL params
        var params = getParams();
        var form = document.getElementById('filterForm');
        var allInputs = form.querySelectorAll('.sf-check input[type="checkbox"]');
        for (var k = 0; k < allInputs.length; k++) {
            var name = allInputs[k].name;
            var value = allInputs[k].value;
            var paramVal = params.get(name);
            if (paramVal && paramVal.split(',').indexOf(value) !== -1) {
                allInputs[k].checked = true;
                var label = allInputs[k].closest('.sf-check').querySelector('.sf-check__label').textContent.trim();
                createChip(name, value, label);
            }
        }

        // Init THC segments
        initSegments();

        // Button states
        updateButtonStates();

        // Reset button
        var resetBtn = document.querySelector('.sf-reset');
        if (resetBtn) {
            resetBtn.addEventListener('click', function(e) {
                e.preventDefault();
                resetAll();
            });
        }

        updateResetVisibility();
    });
})();
