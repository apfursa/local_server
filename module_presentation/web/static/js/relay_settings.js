$(document).ready(function () {

    // Разбираем URL: /relay_settings/65/D1
    const parts = window.location.pathname.split('/');
    const modulId  = parts[parts.length - 2];
    const relayPin = parts[parts.length - 1];

    document.title = `Настройки реле ${modulId}/${relayPin}`;

    let currentMode  = 'force';
    let currentState = 0;
    let allSensors   = [];  // список датчиков для выпадающего списка

    // ==========================================
    // ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    // ==========================================

    function updateStateButton(state, mode) {
        const $btn = $('#btn_state');
        $btn.text(state ? 'ВКЛЮЧЕНО' : 'ВЫКЛЮЧЕНО');
        $btn.removeClass('on off');
        $btn.addClass(state ? 'on' : 'off');

        if (mode === 'force') {
            $btn.removeClass('readonly');
            $('#state_hint').text('Нажмите чтобы изменить');
        } else {
            $btn.addClass('readonly');
            $('#state_hint').text('Управляется автоматически');
        }
    }

    function updateModeButtons(mode) {
        $('#btn_force, #btn_conditions').removeClass('active');
        $(`#btn_${mode}`).addClass('active');
        currentMode = mode;
        updateStateButton(currentState, mode);
    }

    function togglePeriodsAlert() {
        const count = $('#periods_container .period-block').length;
        if (count === 0) {
            $('#no_periods_alert').show();
        } else {
            $('#no_periods_alert').hide();
        }
    }

    function buildConditionRow(sensorId, dataType, operator, value, result) {
        const uid = Date.now() + Math.floor(Math.random() * 1000);

        let sensorOptions = '<option value="">Выберите датчик...</option>';
        allSensors.forEach(function (s) {
            const val = s.sensor_id + '|' + s.data_type;
            const selected = (s.sensor_id == sensorId && s.data_type == dataType) ? 'selected' : '';
            sensorOptions += `<option value="${val}" ${selected}>${s.name || s.sensor_id + '/' + s.data_type}</option>`;
        });

        const operators = ['>', '<', '>=', '<=', '=', '!='];
        let opOptions = operators.map(op =>
            `<option value="${op}" ${op === operator ? 'selected' : ''}>${op}</option>`
        ).join('');

        return `
        <div class="condition-row" data-uid="${uid}">
            <div style="margin-bottom:4px;">
                <select class="cond-sensor" style="width:100%; margin-bottom:0; height:32px; font-size:12px;">${sensorOptions}</select>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr 30px; gap:5px; margin-bottom:4px;">
                <select class="cond-operator" style="margin-bottom:0; height:32px; font-size:12px;">${opOptions}</select>
                <input type="number" step="0.1" class="cond-value" value="${value !== undefined ? value : ''}" style="margin-bottom:0; height:32px; font-size:12px;">
                <button type="button" class="btn-del-condition" data-uid="${uid}">×</button>
            </div>
            <div style="margin-bottom:6px;">
                <select class="cond-result" style="width:100%; margin-bottom:0; height:32px; font-size:12px;">
                    <option value="1" ${result == 1 ? 'selected' : ''}>→ ВКЛЮЧИТЬ</option>
                    <option value="0" ${result == 0 ? 'selected' : ''}>→ ВЫКЛЮЧИТЬ</option>
                </select>
            </div>
        </div>`;
    }
    

    // Строим HTML блока периода
    function buildPeriodBlock(timeStart, timeEnd, conditions) {
        const uid = Date.now() + Math.floor(Math.random() * 1000);
        let conditionsHtml = '';
        if (conditions && conditions.length > 0) {
            conditions.forEach(function (c) {
                conditionsHtml += buildConditionRow(c.sensor_id, c.data_type, c.operator, c.value, c.result);
            });
        }

        return `
        <div class="period-block" data-uid="${uid}">
            <div class="period-header">
                <span>с</span>
                <input type="time" class="period-start" value="${timeStart || '08:00'}">
                <span>до</span>
                <input type="time" class="period-end" value="${timeEnd || '20:00'}">
                <button type="button" class="btn-del-period" data-uid="${uid}">×</button>
            </div>
            <div class="period-body">
                <div class="condition-labels">
                    <span>Датчик</span><span>Условие</span><span>Значение</span><span></span>
                </div>
                <div class="period-conditions-container">${conditionsHtml}</div>
                <button type="button" class="add-period-condition-btn"
                        style="width:100%; margin-top:4px; padding:5px; cursor:pointer; font-size:12px;">
                    ➕ Добавить условие по датчику
                </button>
            </div>
        </div>`;
    }

    // ==========================================
    // ЗАГРУЗКА ДАТЧИКОВ ДЛЯ ВЫПАДАЮЩЕГО СПИСКА
    // ==========================================
    function loadSensors(callback) {
        $.getJSON('/api/latest', function (data) {
            allSensors = data.map(function (s) {
                return {
                    sensor_id: s.sensor_id,
                    data_type: s.type,
                    name: s.name || (s.sensor_id + '/' + s.type)
                };
            });
            if (callback) callback();
        }).fail(function () {
            if (callback) callback();
        });
    }

    // ==========================================
    // ЗАГРУЗКА НАСТРОЕК РЕЛЕ
    // ==========================================
    function loadSettings() {
        $.getJSON(`/api/relay/${modulId}/${relayPin}`, function (data) {
            $('#device_title').text(`Настройки реле (ID ${modulId} / ${relayPin})`);
            $('#relay_name').val(data.name || '');
            $('#ui_type').val(data.ui_type || 'relay');
            $('#offline_timeout').val(data.offline_timeout || 5);

            currentState = data.state || 0;
            currentMode  = data.mode  || 'force';

            updateModeButtons(currentMode);
            updateStateButton(currentState, currentMode);

            loadCategoriesIntoSelects(data.location, data.group);

            // Базовые условия
            $('#base_conditions_container').empty();
            const baseConditions = (data.conditions || []).filter(c => !c.time_start);
            baseConditions.forEach(function (c) {
                $('#base_conditions_container').append(
                    buildConditionRow(c.sensor_id, c.data_type, c.operator, c.value, c.result)
                );
            });

            // Периоды
            $('#periods_container').empty();
            const periods = {};
            (data.conditions || []).filter(c => c.time_start).forEach(function (c) {
                const key = c.time_start + '-' + c.time_end;
                if (!periods[key]) periods[key] = { time_start: c.time_start, time_end: c.time_end, conditions: [] };
                periods[key].conditions.push(c);
            });

            Object.values(periods).forEach(function (p) {
                $('#periods_container').append(buildPeriodBlock(p.time_start, p.time_end, p.conditions));
            });

            togglePeriodsAlert();
        }).fail(function () {
            $('#device_title').text(`Настройки реле (ID ${modulId} / ${relayPin})`);
        });
    }

    // ==========================================
    // ЗАГРУЗКА КАТЕГОРИЙ
    // ==========================================
    function loadCategoriesIntoSelects(selectedLoc, selectedGroup) {
        $.getJSON('/api/categories?type=location', function (data) {
            data.forEach(function (item) {
                const selected = item.name === selectedLoc ? 'selected' : '';
                $('#location_select').append(`<option value="${item.name}" ${selected}>${item.name}</option>`);
            });
        });
        $.getJSON('/api/categories?type=group', function (data) {
            data.forEach(function (item) {
                const selected = item.name === selectedGroup ? 'selected' : '';
                $('#group_select').append(`<option value="${item.name}" ${selected}>${item.name}</option>`);
            });
        });
    }

    // ==========================================
    // ОБРАБОТЧИКИ СОБЫТИЙ
    // ==========================================

    // Переключение режима
    $('#btn_force, #btn_conditions').on('click', function () {
        updateModeButtons($(this).data('mode'));
    });

    // Кнопка состояния (только в режиме Принудительно)
    $('#btn_state').on('click', function () {
        if (currentMode !== 'force') return;
        currentState = currentState ? 0 : 1;
        updateStateButton(currentState, currentMode);
    });

    // Добавить базовое условие
    $('#add_base_condition_btn').on('click', function () {
        $('#base_conditions_container').append(buildConditionRow('', '', '>', '', 1));
    });

    // Удалить базовое условие
    $('#base_conditions_container').on('click', '.btn-del-condition', function () {
        $(this).closest('.condition-row').remove();
    });

    // Добавить период
    $('#add_period_btn').on('click', function () {
        $('#periods_container').append(buildPeriodBlock('08:00', '20:00', []));
        togglePeriodsAlert();
    });

    // Удалить период
    $('#periods_container').on('click', '.btn-del-period', function () {
        $(this).closest('.period-block').remove();
        togglePeriodsAlert();
    });

    // Добавить условие внутри периода
    $('#periods_container').on('click', '.add-period-condition-btn', function () {
        $(this).prev('.period-conditions-container').append(
            buildConditionRow('', '', '>', '', 1)
        );
    });

    // Удалить условие внутри периода
    $('#periods_container').on('click', '.btn-del-condition', function () {
        $(this).closest('.condition-row').remove();
    });

    // ==========================================
    // СОХРАНЕНИЕ
    // ==========================================
    $('#save_btn').on('click', function () {

        // Собираем базовые условия
        const baseConditions = [];
        $('#base_conditions_container .condition-row').each(function () {
            const sensorVal = $(this).find('.cond-sensor').val();
            if (!sensorVal) return;
            const parts = sensorVal.split('|');
            baseConditions.push({
                sensor_id: parseInt(parts[0]),
                data_type: parts[1],
                operator: $(this).find('.cond-operator').val(),
                value: parseFloat($(this).find('.cond-value').val()) || 0,
                result: parseInt($(this).find('.cond-result').val()),
                time_start: null,
                time_end: null
            });
        });

        // Собираем условия из периодов
        const periodConditions = [];
        $('#periods_container .period-block').each(function () {
            const timeStart = $(this).find('.period-start').val();
            const timeEnd   = $(this).find('.period-end').val();
            if (!timeStart || !timeEnd) return;

            $(this).find('.condition-row').each(function () {
                const sensorVal = $(this).find('.cond-sensor').val();
                if (!sensorVal) return;
                const parts = sensorVal.split('|');
                periodConditions.push({
                    sensor_id: parseInt(parts[0]),
                    data_type: parts[1],
                    operator: $(this).find('.cond-operator').val(),
                    value: parseFloat($(this).find('.cond-value').val()) || 0,
                    result: parseInt($(this).find('.cond-result').val()),
                    time_start: timeStart,
                    time_end: timeEnd
                });
            });
        });

        const payload = {
            name: $('#relay_name').val().trim(),
            ui_type: $('#ui_type').val(),
            offline_timeout: parseInt($('#offline_timeout').val()) || 5,
            location: $('#location_select').val(),
            group: $('#group_select').val(),
            mode: currentMode,
            state: currentState,
            conditions: baseConditions.concat(periodConditions)
        };

        $.ajax({
            url: `/api/relay/${modulId}/${relayPin}`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            success: function (response) {
                if (response.status === 'success') {
                    window.location.href = '/';
                } else {
                    alert('Ошибка: ' + response.message);
                }
            },
            error: function (xhr) {
                let msg = 'Ошибка сохранения!';
                if (xhr.responseJSON && xhr.responseJSON.message) msg += '\n' + xhr.responseJSON.message;
                alert(msg);
            }
        });
    });

    // ==========================================
    // СТАРТ
    // ==========================================
    loadSensors(loadSettings);
});
