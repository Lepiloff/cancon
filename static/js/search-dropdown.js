$(document).ready(function() {
    function initSearchDropdown(formSel, dropdownSel) {
        var $form = $(formSel);
        var $dropdown = $(dropdownSel);
        if (!$form.length || !$dropdown.length) return;

        var $results = $dropdown.find('.search-dropdown__results');
        var $close = $dropdown.find('.search-dropdown__close');

        $form.on('submit', function(e) {
            e.preventDefault();
            var q = $form.find('input[name="q"]').val().trim();
            if (!q) return;
            $.ajax({
                url: $form.attr('action'),
                data: $form.serialize(),
                success: function(data) {
                    $results.html(data);
                    $dropdown.addClass('search-dropdown--open');
                }
            });
        });

        $close.on('click', function() {
            $dropdown.removeClass('search-dropdown--open');
        });

        $(document).on('click', function(e) {
            if (!$(e.target).closest(formSel + ',' + dropdownSel).length) {
                $dropdown.removeClass('search-dropdown--open');
            }
        });

        $(document).on('keydown', function(e) {
            if (e.key === 'Escape') $dropdown.removeClass('search-dropdown--open');
        });
    }

    initSearchDropdown('#searchForm', '#searchDropdown');
    initSearchDropdown('#searchFormMobile', '#searchDropdownMobile');
});
