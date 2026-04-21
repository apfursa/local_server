// Словарь соответствий типов и иконок
const UI_ICONS = {
    'leak':   { 0: '✅', 1: '🚨' },
    'door':   { 0: '🟢', 1: '🚪' },
    'motion': { 0: '⚪', 1: '🏃' },
    'smoke':  { 0: '✅', 1: '🔥' },
    'gas':    { 0: '✅', 1: '☣️' },
    'power':  { 0: '🔋', 1: '🔌' },
    'pump':   { 0: '💤', 1: '💦' },
    'gate':   { 0: '🔒', 1: '🔓' },
    'light':  { 0: '🌑', 1: '💡' },
    'fan':    { 0: '⚪', 1: '🌀' }
};

// Функция для получения красивого значения
function getDisplayValue(value, ui_type) {
    // Если этот тип есть в словаре иконок
    if (UI_ICONS[ui_type]) {
        // Округляем (на случай 1.0 или 0.0) и берем иконку
        return UI_ICONS[ui_type][Math.round(value)] || value;
    }
    // Если тип 'numeric' или не найден — возвращаем просто число
    return value;
}

// Функция создания строки (Классическая конкатенация)
function createRow(sensor) {
    let rowId = sensor.id + '_' + sensor.type;
    let displayValue = getDisplayValue(sensor.value, sensor.ui_type);
    return '<tr id="row-' + rowId + '">' +
                '<td style="font-weight: bold; color: #666; text-align: center;">' + sensor.id + '</td>' +
                '<td class="col-name">' +
                    '<form id="form-' + rowId + '" action="/rename" method="post">' +
                        '<input type="hidden" name="sensor_id" value="' + sensor.id + '">' +
                        '<input type="hidden" name="sensor_type" value="' + sensor.type + '">' +
                        '<input type="text" name="new_name" value="' + sensor.name + '" ' +
                        'onchange="confirmRename(\'' + rowId + '\', this)" data-old-value="' + sensor.name + '">' +
                    '</form>' +
                '</td>' +
                '<td class="col-narrow" onclick="toggleChart(\'' + sensor.id + '\', \'' + sensor.type + '\')">' +
                    '<b data-field="value" class="temp-val" style="color: ' + sensor.color + '; font-size: 1.2em;">' + displayValue + '</b>' +
                '</td>' +
                '<td class="col-narrow"><span data-field="time" class="time-val">' + sensor.time + '</span></td>' +
                '<td class="col-narrow">' +
                    '<a href="/settings/' + sensor.id + '?type=' + sensor.type + '" style="text-decoration: none;">⚙️</a>' +
                '</td>' +
            '</tr>' +
            '<tr id="chart-row-' + rowId + '" class="chart-row" style="display: none;">' +
                '<td colspan="5">' +
                    '<div class="chart-container"><canvas id="canvas-' + rowId + '"></canvas></div>' +
                '</td>' +
            '</tr>';
}

function confirmRename(rowId, inputElement) {
    const newName = inputElement.value.trim();
    const oldName = inputElement.getAttribute('data-old-value');
    
    if (newName === oldName || newName === "") {
        return;
    }
    
    // 1. Блокируем инпут, чтобы onblur не сработал случайно еще раз
    inputElement.readOnly = true;

    if (confirm('Изменить название на "' + newName + '"?')) {
        $('#form-' + rowId).submit();
    } else {
        // Если отмена — возвращаем старое имя и разблокируем
        inputElement.value = oldName;
        inputElement.readOnly = false;
    }
}