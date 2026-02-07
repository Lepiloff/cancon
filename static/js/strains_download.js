document.addEventListener('DOMContentLoaded', (event) => {
    let page = 1;
    let btn = document.querySelector('.btn--outline');

    btn.addEventListener('click', function(e) {
        e.preventDefault();

        page++;

        // Получить значения фильтрации
        const category = Array.from(document.querySelector('#filterForm').elements['category'])
            .filter(checkbox => checkbox.checked)
            .map(checkbox => checkbox.value);
        const feelings = Array.from(document.querySelector('#filterForm').elements['feelings'])
            .filter(checkbox => checkbox.checked)
            .map(checkbox => checkbox.value);
        const helps_with = Array.from(document.querySelector('#filterForm').elements['helps_with'])
            .filter(checkbox => checkbox.checked)
            .map(checkbox => checkbox.value);
        const flavors = Array.from(document.querySelector('#filterForm').elements['flavors'])
            .filter(checkbox => checkbox.checked)
            .map(checkbox => checkbox.value);
        const thc = Array.from(document.querySelector('#filterForm').elements['thc'])
            .filter(checkbox => checkbox.checked)
            .map(checkbox => checkbox.value);

        // Создание строки запроса
        const params = new URLSearchParams();
        params.append('page', page);
        category.forEach(item => params.append('category', item));
        feelings.forEach(item => params.append('feelings', item));
        helps_with.forEach(item => params.append('helps_with', item));
        flavors.forEach(item => params.append('flavors', item));
        thc.forEach(item => params.append('thc', item));

        fetch(`/strains/?${params.toString()}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (response.status === 204) {
                const loadMoreButton = document.querySelector('.btn.btn--outline');
                loadMoreButton.disabled = true;
                loadMoreButton.innerText = "No más productos";
            } else {
                return response.text();
            }
        })
        .then(data => {
            if (data) {
                const strainsContainer = document.querySelector('#strainsContainer');
                if (strainsContainer) {
                    // Parse the data as HTML
                    const div = document.createElement('div');
                    div.innerHTML = data.trim();

                    // Select the items to add
                    const newItems = div.querySelectorAll('.ctg__item');

                    // Append the new items
                    newItems.forEach((item) => {
                        strainsContainer.appendChild(item);
                    });
                } else {
                    console.error("Strains container not found");
                }
            }
        })
        .catch(error => {
            console.error("Failed to load strains:", error);
            page--;
            btn.disabled = false;
        });
    });
});
