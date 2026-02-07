$(document).ready(function() {
    // Используйте функцию $ для выбора формы
    var form = $('#filterForm');
    var inputs = form.find('input');

function createChip(name, value) {
    var associatedInput = $('input[name="' + name + '"][value="' + value + '"]');
    var labelText = associatedInput.parent().contents().filter(function() {
        return this.nodeType === 3;  // Выберите только текстовые узлы
    }).text().trim();  // Получаем текстовый узел, следующий за чекбоксом внутри метки

    var chip = $('<div class="ctg__filter_a"></div>');
    chip.append('<span class="mr-15">' + labelText + '</span>');  // Используем labelText
    var remove = $('<div class="ctg__filter_remove"><img src="' + crossUrl + '" alt="" width="15" height="15"></div>');
    chip.append(remove);
    remove.click(function() {
        chip.remove();
        associatedInput.prop('checked', false);
        associatedInput.trigger('change');
    });
    return chip;
}

    var chipContainer = $('<div class="ctg__filter"></div>');
    form.before(chipContainer);

    // Разберите текущие параметры запроса
    var query_string = window.location.search;
    var query_params = new URLSearchParams(query_string);

    // Инициализируйте элементы подсказки для текущих параметров запроса
    for (let i = 0; i < inputs.length; i++) {
        var name = inputs[i].name;
        var value = inputs[i].value;
        if (query_params.get(name) && query_params.get(name).split(',').includes(value)) {
            inputs[i].checked = true;
            var chip = createChip(name, value);
            chipContainer.append(chip);
        }
    }

    for (let i = 0; i < inputs.length; i++) {
        inputs[i].onchange = function() {
            // Добавьте или удалите значения из параметров запроса
            var value = $(this).val();
            var name = $(this).attr('name');

            if (this.checked) {
                if (query_params.has(name)) {
                    query_params.set(name, query_params.get(name) + ',' + value);
                } else {
                    query_params.set(name, value);
                }
                var chip = createChip(name, value);
                chipContainer.append(chip);
            } else {
                var values = query_params.get(name).split(',');
                var index = values.indexOf(value);
                if (index > -1) {
                    values.splice(index, 1);
                }
                    if (values.length === 0) {  // если значений больше нет, удалите параметр
                query_params.delete(name);
            } else {
                query_params.set(name, values.join(','));
            }
                $('.ctg__filter_a:has(span:contains("' + name + '"))').remove();
            }

            // Обновите URL без перезагрузки страницы
            var new_url = window.location.protocol + "//" + window.location.host + window.location.pathname + '?' + query_params.toString();
            window.history.pushState({path: new_url}, '', new_url);
            window.location.href = new_url;
        }
    }
});