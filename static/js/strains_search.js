$(document).ready(function() {
    $('#searchForm').on('submit', function(e) {
        e.preventDefault();
        var form = $(this);
        $.ajax({
            url: form.attr('action'),
            data: form.serialize(),
            success: function(data) {
                $('.modal-body').html(data);
            }
        });
    });
});