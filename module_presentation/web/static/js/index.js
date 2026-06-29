// Текущая конфигурация интерфейса
let uiConfig = { current_view: 'table', group_by: 'none' };
let localCachedData = []; // локальные кэшированные данные
let showOnlyAlerts = false; // показывать только оповещения

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
        $container.html('<div class="no-data-msg">Нет данных от датчиков</div>');
        return;
    }

    // Фильтр только аварий
    let sensorsToDisplay = showOnlyAlerts 
        ? localCachedData.filter(s => s.status_class === 'status-high' || s.status_class === 'status-low' || s.status_class === 'status-black')
        : localCachedData;

    // Группировка
    let groups = {};
    if (uiConfig.group_by !== 'none') {
        sensorsToDisplay.forEach(item => {
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
                <div class="group-title" data-group="${safeName}">
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
                let dMin = sensor.relay_min !== '-' ? sensor.relay_min : sensor.alarm_min;
                let dMax = sensor.relay_max !== '-' ? sensor.relay_max : sensor.alarm_max;

                let enrichedSensor = $.extend({}, sensor, {
                    display_min: dMin,
                    display_max: dMax
                });

                $tbody.append(compileTemplate('#template-table-row', enrichedSensor));
            });
            $target.append($tableLayout);
        } else {
            const $cardLayout = $('<div class="cards-grid-wrapper"></div>');
            sensors.forEach(sensor => {
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
    $.getJSON('/api/latest', function(data) {
        localCachedData = data;
        
        // Считаем только реальные проблемы: аварии (high/low) и обрыв связи (black)
        let alertCount = data.filter(s => 
            s.status_class === 'status-high' || 
            s.status_class === 'status-low' || 
            s.status_class === 'status-black'
        ).length;

        // Ищем или создаем внутри кнопки круглый красный бэйдж
        const $btn = $('#btn-filter-alerts');
        let $badge = $btn.find('.alert-badge-counter');

        if ($badge.length === 0) {
            $btn.append('<span class="alert-badge-counter"></span>');
            $badge = $btn.find('.alert-badge-counter');
        }

        // Если есть аварийные датчики — выводим число, если нет — убираем
        if (alertCount > 0) {
            $badge.text(alertCount);
        } else {
            $badge.text('');
        }

        buildUI();
    }).fail(function(jqXHR, textStatus, errorThrown) {
        console.error("Ошибка при получении /api/latest:", textStatus, errorThrown);
    });
}

// При старте страницы
$(document).ready(function() {
    
    // Инициализация конфигурации UI
    $.getJSON('/api/ui/config', function(config) {
        uiConfig = config;
        
        $('.btn-toggle[data-view]').removeClass('active');
        $('.btn-group-toggle').removeClass('active');

        $(`.btn-toggle[data-view="${uiConfig.current_view}"]`).addClass('active');
        $(`.btn-group-toggle[data-val="${uiConfig.group_by}"]`).addClass('active');
        
        refreshData();
    }).fail(refreshData);

    // Логика выезжающего бургер-меню
    $('#btn-burger-menu').on('click', function() {
        $('#side-menu').addClass('menu-open');
        $('#menu-overlay').addClass('overlay-open');
    });

    $('#menu-overlay').on('click', function() {
        $('#side-menu').removeClass('menu-open');
        $(this).removeClass('overlay-open');
    });

    // Переключение режимов (Таблица / Карточки)
    $('.btn-toggle[data-view]').on('click', function() {
        $('.btn-toggle[data-view]').removeClass('active');
        $(this).addClass('active');
        uiConfig.current_view = $(this).data('view');
        $.ajax({ url: '/api/ui/config', type: 'POST', contentType: 'application/json', data: JSON.stringify(uiConfig) });
        buildUI();
    });

    // Обработчик кнопок группировки
    $(document).on('click', '.btn-group-toggle', function() {
        $('.btn-group-toggle').removeClass('active');
        $(this).addClass('active');
        
        uiConfig.group_by = $(this).data('val');
        
        $.ajax({ 
            url: '/api/ui/config', 
            type: 'POST', 
            contentType: 'application/json', 
            data: JSON.stringify(uiConfig) 
        });
        
        buildUI();
    });

    // Клик по значению (открытие графиков)
    $(document).on('click', '.clickable-trigger', function() {
        const sensorId = $(this).data('sensor-id');
        const dataType = $(this).data('type');
        if (typeof window.toggleChart === 'function') window.toggleChart(sensorId, dataType);
    });

    // Сворачивание/разворачивание групп
    $(document).on('click', '.group-title', function() {
        let groupName = $(this).data('group');
        $(`#group-${groupName}`).slideToggle(200);
        $(this).text($(this).text().includes('⬇️') ? $(this).text().replace('⬇️', '⬆️') : $(this).text().replace('⬆️', '⬇️'));
    });

    // Кнопка фильтра аварий
    $('#btn-filter-alerts').on('click', function() {
        showOnlyAlerts = !showOnlyAlerts; 
        $(this).toggleClass('btn-alert-active', showOnlyAlerts); 
        
        if (showOnlyAlerts) {
            uiConfig.group_by = 'none';
            $('.btn-group-toggle').removeClass('active');
            $('.btn-group-toggle[data-val="none"]').addClass('active');
            
            $.ajax({ 
                url: '/api/ui/config', 
                type: 'POST', 
                contentType: 'application/json', 
                data: JSON.stringify(uiConfig) 
            });
        }
        buildUI();
    });

    setInterval(refreshData, 30000);
});