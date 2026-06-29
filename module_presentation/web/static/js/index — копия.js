// Текущая конфигурация интерфейса
let uiConfig = { current_view: 'table', group_by: 'none' };
let localCachedData = []; // локальные кэшированные данные
let showOnlyAlerts = false; // показывать только оповещения
let isSortMode = false; // включен ли режим ручной сортировки датчиков

// Самописный мини-компилятор строк на чистом JS
function compileTemplate(templateId, dataObj) {
    let html = $(templateId).html();
    if (!html) return '';

    for (let key in dataObj) {
        if (dataObj.hasOwnProperty(key)) {
            let val = dataObj[key];
            let regex = new RegExp(`\\[%\\s*${key}\\s*%\\]`, 'g');
            html = html.replace(regex, val !== undefined && val !== null ? val : '');
        }
    }
    return html;
}

// Сборка и отрисовка интерфейса
function buildUI() {
    const $container = $('#ui-container');
    $container.empty(); 

    if (!localCachedData || localCachedData.length === 0) {
        $container.html('<div style="text-align:center; padding:20px; color:#666;">Нет данных от датчиков</div>');
        return;
    }

    // ==========================================
    // РЕЖИМ СОРТИРОВКИ ДАТЧИКОВ (ТЕХНОЛОГИЧЕСКИЙ)
    // ==========================================
    if (isSortMode) {
        // 1. Отрисовываем каркас таблицы сортировки
        const $sortLayout = $(compileTemplate('#template-sort-layout', {}));
        const $tbody = $sortLayout.find('.table-sort-body-target');

        // 2. В цикле проходим по всем кэшированным датчикам
        localCachedData.forEach((sensor, index) => {
            // Подготавливаем HTML для стрелки "Вверх"
            let btnUp = '<button class="btn-sort-action btn-sort-up">▲</button>';
            // Подготавливаем HTML для стрелки "Вниз"
            let btnDown = '<button class="btn-sort-action btn-sort-down">▼</button>';

            // Если строка ПЕРВАЯ — блокируем ячейку "Вверх"
            if (index === 0) {
                btnUp = ''; 
            }
            // Если строка ПОСЛЕДНЯЯ — блокируем ячейку "Вниз"
            if (index === localCachedData.length - 1) {
                btnDown = '';
            }

            // Обогащаем объект данных датчика кнопками для компилятора шаблонов
            const rowData = $.extend({}, sensor, {
                btn_up: btnUp,
                btn_down: btnDown
            });

            // Компилируем строку и добавляем в таблицу
            const $row = $(compileTemplate('#template-sort-row', rowData));
            
            // Если кнопка пустая, добавим спец-класс для красоты фона ячейки
            if (index === 0) $row.find('.cell-up-action').addClass('cell-sort-disabled');
            if (index === localCachedData.length - 1) $row.find('.cell-down-action').addClass('cell-sort-disabled');

            $tbody.append($row);
        });

        $container.append($sortLayout);
        return; // ВАЖНО: выходим из функции, чтобы обычный интерфейс не строился ниже!
    }

    // ==========================================
    // ОБЫЧНЫЙ РЕЖИМ ОТРИСОВКИ 
    // ==========================================
    // Фильтр только аварий (используем уже готовый статус от сервера)
    let sensorsToDisplay = showOnlyAlerts 
        ? localCachedData.filter(s => s.status_class === 'status-high' || s.status_class === 'status-low')
        : localCachedData;

    // Группировка
    let groups = {};
    if (uiConfig.group_by !== 'none') {
        sensorsToDisplay.forEach(item => {
            // let key = (item.meta && item.meta[uiConfig.group_by]) ? item.meta[uiConfig.group_by] : "Без группы";
            let key = item[uiConfig.group_by] ? item[uiConfig.group_by] : "Без группы";
            if (!groups[key]) groups[key] = [];
            groups[key].push(item);
        });
    } else {
        groups["Все датчики"] = sensorsToDisplay;
    }

    // Отрисовка
    $.each(groups, function(groupName, sensors) {
        let safeName = groupName.replace(/[^a-z0-9]/gi, '-');
        
        if (uiConfig.group_by !== 'none') {
            $container.append(`
                <div class="group-title" data-group="${safeName}" style="cursor:pointer; margin: 20px 0 10px 10px; font-weight: bold; font-size: 1.2em; color: #333; padding: 10px; background: #e0e0e0; border-radius: 5px;">
                    ${groupName} (${sensors.length}) ⬇️
                </div>
                <div class="group-content" id="group-${safeName}"></div>
            `);
        }

        let $target = (uiConfig.group_by !== 'none') ? $(`#group-${safeName}`) : $container;

        if (uiConfig.current_view === 'table') {
            const $tableLayout = $(compileTemplate('#template-table-layout', {}));
            const $tbody = $tableLayout.find('.table-body-target');
            sensors.forEach(sensor => {
                // Вычисляем отображаемый диапазон: приоритет у реле, если его нет — берем аварию
                let dMin = sensor.relay_min !== '-' ? sensor.relay_min : sensor.alarm_min;
                let dMax = sensor.relay_max !== '-' ? sensor.relay_max : sensor.alarm_max;

                // Временно подмешиваем вычисленные значения в объект сенсора для шаблонизатора
                let enrichedSensor = $.extend({}, sensor, {
                    display_min: dMin,
                    display_max: dMax
                });

                $tbody.append(compileTemplate('#template-table-row', enrichedSensor));
            });
            $target.append($tableLayout);
        } else {
            const $cardLayout = $('<div class="cards-layout" style="display: flex; flex-direction: column; gap: 15px; padding: 10px;"></div>');
            sensors.forEach(sensor => {
                // Точно такой же расчет для карточек
                let dMin = sensor.relay_min !== '-' ? sensor.relay_min : sensor.alarm_min;
                let dMax = sensor.relay_max !== '-' ? sensor.relay_max : sensor.alarm_max;

                let enrichedSensor = $.extend({}, sensor, {
                    display_min: dMin,
                    display_max: dMax
                });

                $cardLayout.append(compileTemplate('#template-card', enrichedSensor));
            });
            $target.append($cardLayout);
        }
    });
}

// Загрузка свежего состояния датчиков
function refreshData() {
    // Если включен режим сортировки — полностью блокируем автообновление!
    if (isSortMode) return;
    $.getJSON('/api/latest', function(data) {
        localCachedData = data;
        buildUI();
    }).fail(function(jqXHR, textStatus, errorThrown) {
        console.error("Ошибка при получении /api/latest:", textStatus, errorThrown);
    });
}

// При старте страницы
$(document).ready(function() {
    // $.getJSON('/api/ui/config', function(config) {
    //     uiConfig = config;
    //     $(`.btn-toggle[data-view="${uiConfig.current_view}"]`).addClass('active');
    //     $('#group-select').val(uiConfig.group_by);
    //     refreshData();
    // }).fail(refreshData);

    // ВСТАВЬ ЭТОТ КУСОК НАЧАЛА ИНИЦИАЛИЗАЦИИ:
    $.getJSON('/api/ui/config', function(config) {
        uiConfig = config;
        
        // Сначала очищаем старый активный класс у всех кнопок (для надежности)
        $('.btn-toggle[data-view]').removeClass('active');
        $('.btn-group-toggle').removeClass('active');

        // Подсвечиваем сохранённый вид (Таблица / Карточки)
        $(`.btn-toggle[data-view="${uiConfig.current_view}"]`).addClass('active');
        
        // Подсвечиваем сохранённую группировку (Все / По локациям / По группам) теперь ОНА ТУТ
        $(`.btn-group-toggle[data-val="${uiConfig.group_by}"]`).addClass('active');
        
        refreshData();
    }).fail(refreshData);

    $('.btn-toggle[data-view]').on('click', function() {
        $('.btn-toggle[data-view]').removeClass('active');
        $(this).addClass('active');
        uiConfig.current_view = $(this).data('view');
        $.ajax({ url: '/api/ui/config', type: 'POST', contentType: 'application/json', data: JSON.stringify(uiConfig) });
        buildUI();
    });

    // Обработчик кнопок группировки
    $(document).on('click', '.btn-group-toggle', function() {
        // 1. Убираем класс active у всех кнопок группы
        $('.btn-group-toggle').removeClass('active');
        // 2. Добавляем активной кнопке класс
        $(this).addClass('active');
        
        // 3. Сохраняем значение
        uiConfig.group_by = $(this).data('val');
        
        // 4. Отправляем конфиг на сервер (как вы делали раньше)
        $.ajax({ 
            url: '/api/ui/config', 
            type: 'POST', 
            contentType: 'application/json', 
            data: JSON.stringify(uiConfig) 
        });
        
        // 5. Перерисовываем UI
        buildUI();
    });

    // Плюс, при загрузке страницы подсветим нужную кнопку:
    // Внутри $(document).ready:
    // $(`.btn-group-toggle[data-val="${uiConfig.group_by}"]`).addClass('active');

    $(document).on('click', '.clickable-trigger', function() {
        const sensorId = $(this).data('sensor-id');
        const dataType = $(this).data('type');
        if (typeof window.toggleChart === 'function') window.toggleChart(sensorId, dataType);
    });

    $(document).on('click', '.group-title', function() {
        let groupName = $(this).data('group');
        $(`#group-${groupName}`).slideToggle(200);
        $(this).text($(this).text().includes('⬇️') ? $(this).text().replace('⬇️', '⬆️') : $(this).text().replace('⬆️', '⬇️'));
    });

    $('#btn-filter-alerts').on('click', function() {
        showOnlyAlerts = !showOnlyAlerts; 
        
        // Включаем/выключаем правильный класс анимации и красного цвета
        $(this).toggleClass('btn-alert-active', showOnlyAlerts); 
        
        // НАША НОВАЯ ЛОГИКА: если кнопка "Аварии" была только что ВКЛЮЧЕНА
        if (showOnlyAlerts) {
            // 1. Сбрасываем конфиг группировки в режим "Все"
            uiConfig.group_by = 'none';
            
            // 2. Визуально переключаем кнопки: у всех убираем active, кнопке "Все" добавляем
            $('.btn-group-toggle').removeClass('active');
            $('.btn-group-toggle[data-val="none"]').addClass('active');
            
            // 3. Отправляем обновленный конфиг на сервер, чтобы он там тоже сохранился
            $.ajax({ 
                url: '/api/ui/config', 
                type: 'POST', 
                contentType: 'application/json', 
                data: JSON.stringify(uiConfig) 
            });
        }
        
        // Перестраиваем интерфейс
        buildUI();
    });

    // ==========================================
    // ЛОГИКА ГЛОБАЛЬНОГО GSM НОМЕРА
    // ==========================================

    // 1. По клику на кнопку плавно открываем/закрываем панель
    $('#btn-phone-trigger').on('click', function() {
        // ЕСЛИ МЫ БЫЛИ В РЕЖИМЕ СОРТИРОВКИ: любое повторное нажатие на "Сервис" — это ОТМЕНА
        if (isSortMode) {
            location.reload(); // Просто жестко перезагружаем страницу, сбрасывая всё
            return;
        }

        $(this).toggleClass('active');
        $('#phone-settings-panel').slideToggle(200);

        // Если панель открылась, запрашиваем актуальный номер из новой таблицы базы данных
        if ($(this).hasClass('active')) {
            $.getJSON('/api/settings/admin_phone', function(data) {
                if (data && data.value) {
                    $('#global_admin_phone').val(data.value).css('border-color', '#aaa');
                } else {
                    $('#global_admin_phone').val('').attr('placeholder', 'Не задан! Введите +7...');
                    $('#global_admin_phone').css('border-color', 'red');
                }
            }).fail(function() {
                console.error("Не удалось загрузить глобальный номер телефона.");
            });
        }
    });

    // 2. Сохранение номера телефона по кнопке ОК
    $('#btn-save-phone').on('click', function() {
        const phoneValue = $('#global_admin_phone').val().trim();

        if (phoneValue === "") {
            alert('Поле номера не может быть пустым!');
            return;
        }

        if (!phoneValue.startsWith('+')) {
            alert('Номер должен начинаться с плюса и содержать код страны (например, +7...)');
            return;
        }

        // Отправляем в наш переписанный под новую таблицу контроллер Flask
        $.ajax({
            url: '/api/settings/admin_phone',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ value: phoneValue }),
            success: function(response) {
                if (response.status === 'success') {
                    alert('Номер успешно сохранен в глобальных настройках!');
                    $('#global_admin_phone').css('border-color', '#aaa');
                    // Закрываем панель
                    $('#btn-phone-trigger').removeClass('active');
                    $('#phone-settings-panel').slideUp(200);
                } else {
                    alert('Ошибка сервера: ' + response.message);
                }
            },
            error: function() {
                alert('Критическая ошибка при сохранении номера!');
            }
        });
    });

    // ==========================================
    // ЛОГИКА ВХОДА В РЕЖИМ СОРТИРОВКИ
    // ==========================================
    $('#btn-sort-start').on('click', function() {
        isSortMode = true;

        // 1. Прячем блок ввода телефона и саму кнопку "Порядок"
        $('#phone-input-block').hide();
        $('#btn-sort-start').hide();

        // 2. Показываем кнопку "Готово"
        $('#btn-sort-submit').show();

        // 3. Жестко переключаем внутренний конфиг в режим "Таблица" без группировки
        uiConfig.current_view = 'table';
        uiConfig.group_by = 'none';

        // 4. Подсвечиваем правильные кнопки в основном меню управления, чтобы визуально всё соответствовало
        $('.btn-toggle[data-view]').removeClass('active');
        $('.btn-toggle[data-view="table"]').addClass('active');
        
        $('.btn-group-toggle').removeClass('active');
        $('.btn-group-toggle[data-val="none"]').addClass('active');

        // 5. Вызываем функцию перерисовки (её мы напишем на следующем шаге)
        buildUI();
    });

    // ==========================================
    // ДВИЖЕНИЕ СТРОК В РЕЖИМЕ СОРТИРОВКИ (▲ / ▼)
    // ==========================================

    // Клик по стрелке ВВЕРХ (▲)
    $(document).on('click', '.btn-sort-up', function() {
        const $currentRow = $(this).closest('.sort-item-row');
        const $prevRow = $currentRow.prev('.sort-item-row');

        // Если выше есть строка — меняем их местами в DOM
        if ($prevRow.length > 0) {
            // Получаем индексы элементов в нашем массиве
            const currentIndex = $currentRow.index();
            const prevIndex = $prevRow.index();

            // Переставляем элементы местами в localCachedData
            const temp = localCachedData[currentIndex];
            localCachedData[currentIndex] = localCachedData[prevIndex];
            localCachedData[prevIndex] = temp;

            // Визуально двигаем строку вверх
            $currentRow.insertBefore($prevRow);

            // Перерисовываем интерфейс, чтобы правильно пересчитались крайние заблокированные стрелки
            buildUI();
        }
    });

    // Клик по стрелке ВНИЗ (▼)
    $(document).on('click', '.btn-sort-down', function() {
        const $currentRow = $(this).closest('.sort-item-row');
        const $nextRow = $currentRow.next('.sort-item-row');

        // Если ниже есть строка — меняем их местами в DOM
        if ($nextRow.length > 0) {
            // Получаем индексы элементов в нашем массиве
            const currentIndex = $currentRow.index();
            const nextIndex = $nextRow.index();

            // Переставляем элементы местами в localCachedData
            const temp = localCachedData[currentIndex];
            localCachedData[currentIndex] = localCachedData[nextIndex];
            localCachedData[nextIndex] = temp;

            // Визуально двигаем строку вниз
            $currentRow.insertAfter($nextRow);

            // Перерисовываем интерфейс, чтобы правильно пересчитались крайние заблокированные стрелки
            buildUI();
        }
    });

    // ==========================================
    // СОХРАНЕНИЕ НОВОГО ПОРЯДКА НА СЕРВЕР (ГОТОВО)
    // ==========================================
    $('#btn-sort-submit').on('click', function() {
        const sortedPayload = [];

        // Проходимся по строкам таблицы в том порядке, в котором они СЕЙЧАС лежат в DOM
        $('.sort-item-row').each(function() {
            const sensorId = $(this).data('sensor-id');
            const dataType = $(this).data('type');

            if (sensorId !== undefined && dataType !== undefined) {
                sortedPayload.push({
                    sensor_id: sensorId,
                    type: dataType
                });
            }
        });

        // Отправляем сформированный JSON на сервер
        $.ajax({
            url: '/api/settings/save_sort_order', // URL бэкенда для сохранения порядка
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(sortedPayload),
            success: function(response) {
                if (response.status === 'success') {
                    // Всё прошло успешно — перезагружаем страницу для отображения нового порядка
                    location.reload();
                } else {
                    alert('Ошибка сервера при сохранении порядка: ' + response.message);
                }
            },
            error: function() {
                alert('Критическая ошибка при отправке нового порядка на сервер!');
            }
        });
    });

    setInterval(refreshData, 30000);
});