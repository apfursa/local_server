// function loadList() {
//     $.getJSON('/api/categories', function(data) {
//         $('#cat_list').empty();
//         data.forEach(item => {
//             $('#cat_list').append(`<tr><td>${item.type}</td><td>${item.name}</td></tr>`);
//         });
//     });
// }

// function addCategory() {
//     let name = $('#cat_name').val().trim(); // .trim() уберет лишние пробелы
//     let type = $('#cat_type').val();
//     if (name === "") {
//         alert("Введите название!");
//         return;
//     }
//     $.ajax({
//         url: '/api/categories',
//         type: 'POST',
//         contentType: 'application/json',
//         data: JSON.stringify({name: name, type: type}),
//         success: function() { loadList(); $('#cat_name').val(''); }
//     });
// }

function loadList() {
    $.getJSON('/api/categories', function(data) {
        $('#cat_list').empty();
        
        // 1. Сортировка: сначала location, потом group. Внутри каждого типа — по алфавиту (name)
        data.sort((a, b) => {
            if (a.type !== b.type) {
                // 'location' по алфавиту идет раньше, чем 'group', поэтому сортируем по убыванию типа
                return b.type.localeCompare(a.type); 
            }
            // Если типы одинаковые — сортируем по названию (А-Я)
            return a.name.localeCompare(b.name);
        });

        // 2. Отрисовка списка с переводом и кнопкой удаления
        data.forEach(item => {
            let typeRu = (item.type === 'location') ? 'Локация' : 'Группа';
            
            // Используем ID элемента, если его нет в объекте — передаем name и type
            let deleteArgs = item.id ? item.id : JSON.stringify({name: item.name, type: item.type});
            
            $('#cat_list').append(`
                <tr>
                    <td><span class="badge-type type-${item.type}">${typeRu}</span></td>
                    <td class="cat-name-cell">${item.name}</td>
                    <td style="text-align: center;">
                        <button class="btn-del-cat" onclick='deleteCategory(${item.id ? item.id : JSON.stringify(item)})'>&times;</button>
                    </td>
                </tr>
            `);
        });
    });
}

function addCategory() {
    let name = $('#cat_name').val().trim(); 
    let type = $('#cat_type').val();
    if (name === "") {
        alert("Введите название!");
        return;
    }
    $.ajax({
        url: '/api/categories',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({name: name, type: type}),
        success: function() { 
            loadList(); 
            $('#cat_name').val(''); 
        }
    });
}

function deleteCategory(target) {
    if (!confirm("Удалить этот справочник?")) return;

    // Определяем, слать ID или объект (в зависимости от структуры твоей бд)
    let ajaxData = typeof target === 'object' ? JSON.stringify(target) : JSON.stringify({id: target});

    $.ajax({
        url: '/api/categories',
        type: 'DELETE',
        contentType: 'application/json',
        data: ajaxData,
        success: function() {
            loadList();
        },
        error: function() {
            alert("Ошибка при удалении!");
        }
    });
}

$(document).ready(loadList);