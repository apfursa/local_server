let editCategoryId = null; // Глобальная переменная для хранения ID редактируемой строки

function loadList() {
    $.getJSON('/api/categories', function(data) {
        $('#cat_list').empty();
        
        // 1. Сортировка
        data.sort((a, b) => {
            if (a.type !== b.type) {
                return b.type.localeCompare(a.type); 
            }
            return a.name.localeCompare(b.name);
        });

        // 2. Отрисовка списка
        data.forEach(item => {
            let typeRu = (item.type === 'location') ? 'Локация' : 'Группа';
            let safeName = item.name.replace(/'/g, "\\'").replace(/"/g, '&quot;');

            // Добавили классы cat-row и cat-row-${item.type} для последующей фильтрации
            $('#cat_list').append(`
                <tr id="cat_row_${item.id}" class="cat-row cat-row-${item.type}">
                    <td><span class="badge-type type-${item.type}">${typeRu}</span></td>
                    <td class="cat-name-cell">${item.name}</td>
                    <td style="text-align: center;">
                        <button class="btn-edit-cat" onclick="startEdit(${item.id}, '${safeName}', '${item.type}')">✏️</button>
                    </td>
                    <td style="text-align: center;">
                        <button class="btn-del-cat" onclick="deleteCategory(${item.id})">&times;</button>
                    </td>
                </tr>
            `);
        });

        // Возвращаем подсветку строки, если редактировали
        if (editCategoryId !== null) {
            $(`#cat_row_${editCategoryId}`).addClass('row-editing-active');
        }
        // Пинаем тумблер строго ПОСЛЕ того, как таблица полностью собралась
        $('input[name="cat_type"]').trigger('change');
    });
}

// Перевод формы и верхнего бара в режим редактирования
function startEdit(id, name, type) {
    editCategoryId = id;
    
    // 1. Заполняем поля формы данными из выбранной строки
    $('#cat_name').val(name);
    $(`input[name="cat_type"][value="${type}"]`).prop('checked', true).trigger('change');
    
    // 2. Переобуваем кнопки в sticky-action-bar
    $('#btn_back').text('Отмена').css('background', '#f39c12'); // Делаем оранжевой под цвет карандаша
    $('#btn_save').text('Сохранить');
    
    // 3. Подсвечиваем активную строку в таблице
    $('.cat-table tbody tr').removeClass('row-editing-active');
    $(`#cat_row_${id}`).addClass('row-editing-active');
    
    // Плавный скролл к форме, чтобы на мобилке сразу было видно заполненные поля
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Отмена редактирования — возвращаем всё в исходное состояние
function cancelEdit() {
    editCategoryId = null;
    
    // 1. Очищаем инпуты
    $('#cat_name').val('');
    $('#type_location').prop('checked', true).trigger('change'); // возвращаем дефолт на Локацию
    
    // 2. Возвращаем исходный вид кнопкам в баре
    $('#btn_back').text('← Назад').css('background', '#7f8c8d'); // возвращаем серый цвет
    $('#btn_save').text('Добавить');
    
    // 3. Убираем подсветку строки
    $('.cat-table tbody tr').removeClass('row-editing-active');
}

// Обработчик для левой кнопки (Назад / Отмена)
$('#btn_back').on('click', function(e) {
    if (editCategoryId !== null) {
        e.preventDefault(); // Отменяем переход по ссылке "/"
        cancelEdit();       // Просто сбрасываем режим редактирования
    }
});

// Единый обработчик для правой кнопки (Добавить / Сохранить)
$('#btn_save').on('click', function() {
    let name = $('#cat_name').val().trim(); 
    let type = $('input[name="cat_type"]:checked').val();
    
    if (name === "") {
        alert("Введите название!");
        return;
    }
    
    if (editCategoryId === null) {
        // --- РЕЖИМ ДОБАВЛЕНИЯ (POST) ---
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
    } else {
        // --- РЕЖИМ РЕДАКТИРОВАНИЯ (PUT) ---
        $.ajax({
            url: '/api/categories',
            type: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({id: editCategoryId, name: name, type: type}),
            success: function() { 
                cancelEdit(); // Возвращаем кнопкам исходный вид и чистим форму
                loadList();   // Перезагружаем таблицу
            },
            error: function(jqXHR) {
                alert("Ошибка при сохранении изменений: " + (jqXHR.responseJSON?.error || "неизвестная ошибка"));
            }
        });
    }
});

function deleteCategory(target) {
    // Если удаляем строку, которую прямо сейчас редактируем — сбросим форму в исходное состояние
    let targetId = typeof target === 'object' ? target.id : target;
    if (editCategoryId !== null && editCategoryId == targetId) {
        cancelEdit();
    }

    if (!confirm("Удалить этот справочник?")) return;

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

// Клик по самому ОВАЛУ — переключает триггер на противоположный
$(document).on('click', '.cat-switch-wrapper', function(e) {
    e.preventDefault();
    e.stopPropagation();
    
    // Проверяем, что сейчас выбрано
    let isLocation = $('#type_location').prop('checked');
    
    // Включаем противоположный инпут
    if (isLocation) {
        $('#type_group').prop('checked', true).trigger('change');
    } else {
        $('#type_location').prop('checked', true).trigger('change');
    }
});

// Клик по тексту "Локация" (слева)
$(document).on('click', '.label-left', function(e) { 
    e.preventDefault();
    e.stopPropagation();
    $('#type_location').prop('checked', true).trigger('change'); 
});

// Клик по тексту "Группа" (справа)
$(document).on('click', '.label-right', function(e) { 
    e.preventDefault();
    e.stopPropagation();
    $('#type_group').prop('checked', true).trigger('change'); 
});

// Живая подсветка текста и фильтрация таблицы в зависимости от положения тумблера
$(document).on('change', 'input[name="cat_type"]', function(e) {
    let checkedInput = $('input[name="cat_type"]:checked');
    let currentType = checkedInput.length > 0 ? checkedInput.val() : 'location';
    
    // --- НАЧАЛО БЛОКА ФИЛЬТРАЦИИ ТАБЛИЦЫ ---
    $('.cat-row').hide(); // Сначала мгновенно прячем вообще все строки
    $(`.cat-row-${currentType}`).show(); // Показываем только строки выбранного типа
    // --- КОНЕЦ БЛОКА ФИЛЬТРАЦИИ ТАБЛИЦЫ ---

    if (currentType === 'location') {
        $('.label-left').css('color', '#2980b9'); 
        $('.label-right').css('color', '#7f8c8d'); 
    } else {
        $('.label-left').css('color', '#7f8c8d');  
        $('.label-right').css('color', '#8e44ad'); 
    }
});

// Запуск при загрузке страницы
$(document).ready(function() {
    loadList(); // Просто вызываем загрузку, она сама всё отфильтрует в конце
});