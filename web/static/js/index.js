// Текущая конфигурация интерфейса
let uiConfig = { current_view: 'table', group_by: 'none' };
let localCachedData = [];

// Словарь для бинарных датчиков и оборудования
const UI_ICONS = {
    'leak':   { 0: '✅ Чисто', 1: '🚨 ПРОТЕЧКА!' },
    'door':   { 0: '🟢 Закрыто', 1: '🚪 ОТКРЫТО' },
    'motion': { 0: '⚪ Спокойно', 1: '🏃 ДВИЖЕНИЕ' },
    'smoke':  { 0: '✅ Чисто', 1: '🔥 ДЫМ!' },
    'gas':    { 0: '✅ Норма', 1: '☣️ ГАЗ!' },
    'power':  { 0: '🔋 Батарея', 1: '🔌 Сеть 220В' },
    'pump':   { 0: '💤 Спит', 1: '💦 ПОЛИВ' },
    'gate':   { 0: '🔒 Закрыто', 1: '🔓 Открыто' },
    'light':  { 0: '🌑 Выкл', 1: '💡 Включен' },
    'fan':    { 0: '⚪ Выкл', 1: '🌀 Обдув' }
};

// Функция перевода значений в иконки/текст с двойной проверкой
function getDisplayValue(value, ui_type, type) {
    if (ui_type && ui_type !== 'numeric' && UI_ICONS[ui_type]) {
        return UI_ICONS[ui_type][Math.round(value)] || value;
    }
    if (UI_ICONS[type]) {
        return UI_ICONS[type][Math.round(value)] || value;
    }
    return value;
}

// Самописный мини-компилятор строк на чистом JS
function compileTemplate(templateId, dataObj) {
    let html = $(templateId).html();
    if (!html) return '';

    for (let key in dataObj) {
        if (dataObj.hasOwnProperty(key)) {
            let val = dataObj[key];
            // Ищет [% ключ %] или [%ключ%] средствами регулярных выражений JS
            let regex = new RegExp(`\\[%\\s*${key}\\s*%\\]`, 'g');
            html = html.replace(regex, val !== undefined && val !== null ? val : '');
        }
    }
    return html;
}

// Превращение вложенного JSON от Flask в плоский объект
function flattenSensorObject(sensor) {
    let meta = sensor.meta || {};
    let sData = sensor.data || {};
    let thresholds = sensor.thresholds || {};

    let flat = {
        uid: sensor.uid,
        sensor_id: sensor.sensor_id,
        type: sensor.type || 'temp',

        name: meta.name || `Модуль ${sensor.sensor_id}`,
        unit: meta.unit || '',
        ui_type: meta.ui_type || 'numeric',
        location: meta.location || 'Улица',
        group: meta.group || 'Климат',

        value: sData.value !== undefined ? sData.value : 0,
        timestamp: sData.timestamp || 0,
        time_str: sData.time_str || '--:--:--',
        is_online: sData.is_online !== undefined ? sData.is_online : true,

        min: thresholds.min !== undefined ? thresholds.min : 18.0,
        max: thresholds.max !== undefined ? thresholds.max : 28.0
    };

    flat.display_value = getDisplayValue(flat.value, flat.ui_type, flat.type);
    flat.offline_class = flat.is_online ? '' : 'offline_class';

    // Цветовая индикация аварийных порогов
    flat.status_class = 'status-ok';
    if (!flat.is_online) {
        flat.status_class = 'status-offline';
    } else if (flat.value > flat.max || flat.value < flat.min) {
        flat.status_class = 'status-danger';
    } else if (flat.type.indexOf('temp') === 0 && flat.value > (flat.max * 0.9)) {
        flat.status_class = 'status-warning';
    }

    return flat;
}

// Сборка и отрисовка интерфейса на экране
function buildUI() {
    const $container = $('#ui-container');
    $container.empty();

    if (!localCachedData || localCachedData.length === 0) {
        $container.html('<div style="text-align:center; padding:20px; color:#666;">Нет данных от датчиков</div>');
        return;
    }

    let groups = {};
    if (uiConfig.group_by !== 'none') {
        localCachedData.forEach(item => {
            let key = (item.meta && item.meta[uiConfig.group_by]) ? item.meta[uiConfig.group_by] : "Без группы";
            if (!groups[key]) groups[key] = [];
            groups[key].push(item);
        });
    } else {
        groups["Все датчики"] = localCachedData;
    }

    $.each(groups, function(groupName, sensors) {
        if (uiConfig.group_by !== 'none') {
            $container.append(`<div class="group-title" style="margin: 20px 0 10px 10px; font-weight: bold; font-size: 1.2em; color: #333;">${groupName} (${sensors.length})</div>`);
        }

        if (uiConfig.current_view === 'table') {
            const $tableLayout = $(compileTemplate('#template-table-layout', {}));
            const $tbody = $tableLayout.find('.table-body-target');

            sensors.forEach(sensor => {
                let flat = flattenSensorObject(sensor);
                $tbody.append(compileTemplate('#template-table-row', flat));
            });
            $container.append($tableLayout);
        } else {
            const $cardLayout = $('<div class="cards-layout" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; padding: 10px;"></div>');
            sensors.forEach(sensor => {
                let flat = flattenSensorObject(sensor);
                $cardLayout.append(compileTemplate('#template-card', flat));
            });
            $container.append($cardLayout);
        }
    });
}

// Загрузка свежего состояния датчиков через стандартный AJAX jQuery
function refreshData() {
    $.getJSON('/api/latest', function(data) {
        localCachedData = data;
        buildUI();
    }).fail(function(jqXHR, textStatus, errorThrown) {
        console.error("Ошибка при получении /api/latest:", textStatus, errorThrown);
    });
}

function toggleChart(sensorId, dataType) {
    if (typeof window.showChartForDevice === 'function') {
        window.showChartForDevice(sensorId, dataType);
    } else {
        console.log(`Запрос графика для датчика ${sensorId} [${dataType}]`);
    }
}

function confirmRename(rowId, inputElement) {
    const newName = inputElement.value.trim();
    const oldName = inputElement.getAttribute('data-old-value');
    if (newName === oldName || newName === "") return;

    inputElement.readOnly = true;
    if (confirm(`Изменить название на "${newName}"?`)) {
        $('#form-' + rowId).submit();
    } else {
        inputElement.value = oldName;
        inputElement.readOnly = false;
    }
}

// При старте страницы
$(document).ready(function() {
    $.getJSON('/api/ui/config', function(config) {
        uiConfig = config;
        $(`.btn-toggle[data-view="${uiConfig.current_view}"]`).addClass('active').siblings().removeClass('active');
        $('#group-select').val(uiConfig.group_by);
        refreshData();
    }).fail(function() {
        refreshData();
    });

    $('.btn-toggle').on('click', function() {
        $(this).addClass('active').siblings().removeClass('active');
        uiConfig.current_view = $(this).data('view');

        $.ajax({
            url: '/api/ui/config',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(uiConfig)
        });
        buildUI();
    });

    $('#group-select').on('change', function() {
        uiConfig.group_by = $(this).val();

        $.ajax({
            url: '/api/ui/config',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(uiConfig)
        });
        buildUI();
    });

    setInterval(refreshData, 30000);
});