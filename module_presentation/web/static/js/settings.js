$(document).ready(function() {
    // Вытаскиваем ID из пути: /settings/39 -> 39
    const sensorId = window.location.pathname.split('/').pop();
    if (sensorId) {
        document.title = `Настройки модуля ${sensorId}`;
    }
    
    // Вытаскиваем тип из параметров: ?type=hum -> hum (по умолчанию temp)
    const urlParams = new URLSearchParams(window.location.search);
    const dataType = urlParams.get('type') || 'temp';

    // ==========================================
    // ЛОГИКА ИНТЕРФЕЙСА РАСПИСАНИЯ
    // ==========================================

    // Функция добавления нового блока периода (3 строки, объединенные кнопкой удаления через rowspan)
    function addPeriodRow(timeStart = '', timeEnd = '', alarmMin = '', relayMin = '', relayMax = '', alarmMax = '') {
        // Генерируем уникальный маркер для этой группы строк
        const periodIndex = Date.now() + Math.floor(Math.random() * 100);

        const rowHtml = `
            <tr data-period="${periodIndex}">
                <td>
                    <div class="sched-row-flex">
                        <div class="input-group">
                            <label>Старт</label>
                            <input type="time" class="schedule-start" value="${timeStart}" required>
                        </div>
                        <div class="input-group">
                            <label>Конец</label>
                            <input type="time" class="schedule-end" value="${timeEnd}" required>
                        </div>
                    </div>
                </td>
                <td rowspan="3" class="delete-cell-merged">
                    <button type="button" class="btn-delete-period-merged" title="Удалить" data-target="${periodIndex}">×</button>
                </td>
            </tr>

            <tr data-period="${periodIndex}">
                <td>
                    <div class="sched-row-flex">
                        <div class="input-group">
                            <label>Авария Мин</label>
                            <input type="number" step="0.1" class="schedule-alarm-min" value="${alarmMin !== null ? alarmMin : ''}" placeholder="нет">
                        </div>
                        <div class="input-group">
                            <label>Реле Мин</label>
                            <input type="number" step="0.1" class="schedule-relay-min" value="${relayMin !== null ? relayMin : ''}" placeholder="нет">
                        </div>
                    </div>
                </td>
            </tr>

            <tr data-period="${periodIndex}">
                <td>
                    <div class="sched-row-flex">
                        <div class="input-group">
                            <label>Реле Макс</label>
                            <input type="number" step="0.1" class="schedule-relay-max" value="${relayMax !== null ? relayMax : ''}" placeholder="нет">
                        </div>
                        <div class="input-group">
                            <label>Авария Макс</label>
                            <input type="number" step="0.1" class="schedule-alarm-max" value="${alarmMax !== null ? alarmMax : ''}" placeholder="нет">
                        </div>
                    </div>
                </td>
            </tr>
        `;
        $('#schedules_container').append(rowHtml);
    }

    // Управление видимостью таблицы и заглушки
    function toggleNoSchedulesAlert() {
        // Считаем количество уникальных data-period блоков (берём по первой строке каждого блока)
        const rowsCount = $('#schedules_container tr[data-period]').length / 3;
        if (rowsCount === 0) {
            $('#no_schedules_alert').show();
            $('#schedules_table').hide();
        } else {
            $('#no_schedules_alert').hide();
            $('#schedules_table').show();
        }
    }

    // Клик по кнопке "Добавить период"
    $('#add_period_btn').on('click', function() {
        addPeriodRow('08:00', '20:00', '', '', '', '');
        toggleNoSchedulesAlert();
    });

    // Удаление всего блока периода по клику на крестик
    $('#schedules_container').on('click', '.btn-delete-period-merged', function() {
        const targetIndex = $(this).data('target');
        // Находим и удаляем все 3 строки, у которых совпадает data-period
        $(`#schedules_container tr[data-period="${targetIndex}"]`).remove();
        toggleNoSchedulesAlert();
    });


    // ==========================================
    // ЛОГИКА ДЛЯ БЛОКА ГЛУШЕНИЯ (MUTE)
    // ==========================================

    // Вспомогательная функция для выставления значений в ручные инпуты
    function setManualMuteFields(dateObject) {
        if (!dateObject) {
            $('#mute_date').val('');
            $('#mute_time').val('');
            return;
        }
        
        let year = dateObject.getFullYear();
        let month = String(dateObject.getMonth() + 1).padStart(2, '0');
        let day = String(dateObject.getDate()).padStart(2, '0');
        $('#mute_date').val(`${year}-${month}-${day}`);
        
        let hours = String(dateObject.getHours()).padStart(2, '0');
        let minutes = String(dateObject.getMinutes()).padStart(2, '0');
        $('#mute_time').val(`${hours}:${minutes}`);
    }

    // Обработка кликов по кнопкам быстрого глушения
    $('.btn-mute-quick').on('click', function() {
        let now = new Date();
        let hoursToAdd = $(this).data('hours');

        if (hoursToAdd) {
            now.setHours(now.getHours() + parseInt(hoursToAdd));
            setManualMuteFields(now);
        } else {
            setManualMuteFields(null);
        }
    });


    // ==========================================
    // 1. ЗАГРУЗКА БАЗОВЫХ ДАННЫХ И НАСТРОЕК (GET)
    // ==========================================
    $.getJSON(`/api/settings/${sensorId}?type=${dataType}`, function(data) {
        $('#sensor_name').val(data.name || '');
        
        // Заполняем новые 4 инпута базовых порогов плитки 2х2
        $('#edit_alarm_min').val(data.alarm_min);
        $('#edit_relay_min').val(data.relay_min);
        $('#edit_relay_max').val(data.relay_max);
        $('#edit_alarm_max').val(data.alarm_max);
        
        // Разбираем mute_until от сервера
        if (data.mute_until) {
            let parts = data.mute_until.split(/[T ]/);
            if (parts[0]) $('#mute_date').val(parts[0]);
            if (parts[1]) $('#mute_time').val(parts[1].substring(0, 5));
        } else {
            $('#mute_date').val('');
            $('#mute_time').val('');
        }

        loadCategoriesIntoSelects(data.location, data.group);
        $('#device_title').text(`Настройки: ${dataType} (ID ${sensorId})`);

        setTimeout(function() {
            const typeToSet = data.ui_type || 'numeric';
            $('#ui_type').val(typeToSet).change();
        }, 10);
    }).fail(function() {
        $('#device_title').text(`Настройки: ${dataType} (ID ${sensorId})`);
    });


    // ==========================================
    // 2. ЗАГРУЗКА СУЩЕСТВУЮЩЕГО РАСПИСАНИЯ (GET)
    // ==========================================
    function loadSchedulesFromServer() {
        $.getJSON(`/api/schedules/${sensorId}?type=${dataType}`, function(data) {
            $('#schedules_container').empty();
            
            if (data && data.length > 0) {
                data.forEach(function(period) {
                    // Передаем все 4 новые уставки из базы в генератор строк
                    addPeriodRow(
                        period.time_start, 
                        period.time_end, 
                        period.alarm_min, 
                        period.relay_min, 
                        period.relay_max, 
                        period.alarm_max
                    );
                });
            }
            toggleNoSchedulesAlert();
        }).fail(function() {
            console.error("Не удалось загрузить расписание для этого датчика.");
            toggleNoSchedulesAlert();
        });
    }

    loadSchedulesFromServer();

    // Функция загрузки справочников в выпадающие списки
    function loadCategoriesIntoSelects(selectedLoc, selectedGroup) {
        $.getJSON('/api/categories?type=location', function(data) {
            data.forEach(item => {
                let selected = (item.name === selectedLoc) ? 'selected' : '';
                $('#location_select').append(`<option value="${item.name}" ${selected}>${item.name}</option>`);
            });
        });

        $.getJSON('/api/categories?type=group', function(data) {
            data.forEach(item => {
                let selected = (item.name === selectedGroup) ? 'selected' : '';
                $('#group_select').append(`<option value="${item.name}" ${selected}>${item.name}</option>`);
            });
        });
    }


    // ==========================================
    // 3. СОХРАНЕНИЕ ДАННЫХ (POST)
    // ==========================================
    $('#save_btn').on('click', function() {
        const schedulesArray = [];
        
        // Массив для хранения обработанных индексов, чтобы не дублировать сборку из-за 3-х строк
        const processedPeriods = [];

        // Итерируемся по строкам расписания
        $('#schedules_container tr[data-period]').each(function() {
            const periodId = $(this).data('period');

            // Если этот блок уставки мы уже считали на текущей итерации — пропускаем
            if (processedPeriods.includes(periodId)) return;
            processedPeriods.push(periodId);

            // Находим конкретные строки этой группы
            const rows = $(`#schedules_container tr[data-period="${periodId}"]`);
            
            const timeStart = rows.find('.schedule-start').val();
            const timeEnd = rows.find('.schedule-end').val();
            
            const alarmMin = rows.find('.schedule-alarm-min').val();
            const relayMin = rows.find('.schedule-relay-min').val();
            const relayMax = rows.find('.schedule-relay-max').val();
            const alarmMax = rows.find('.schedule-alarm-max').val();
            
            // В расписание сохраняем период, если задано время
            if (timeStart && timeEnd) {
                schedulesArray.push({
                    time_start: timeStart,
                    time_end: timeEnd,
                    alarm_min: alarmMin && alarmMin.trim() !== "" && !isNaN(parseFloat(alarmMin)) ? parseFloat(alarmMin) : null,
                    relay_min: relayMin && relayMin.trim() !== "" && !isNaN(parseFloat(relayMin)) ? parseFloat(relayMin) : null,
                    relay_max: relayMax && relayMax.trim() !== "" && !isNaN(parseFloat(relayMax)) ? parseFloat(relayMax) : null,
                    alarm_max: alarmMax && alarmMax.trim() !== "" && !isNaN(parseFloat(alarmMax)) ? parseFloat(alarmMax) : null
                });
            }
        });

        // Склеиваем дату и время обратно для сервера
        let muteUntilPayload = null;
        const mDate = $('#mute_date').val();
        const mTime = $('#mute_time').val();

        if (mDate && mTime) {
            muteUntilPayload = `${mDate}T${mTime}:00`;
        }

        // Формируем payload под новые 4 параметра (исправлен селектор relay_max)
        const payload = {
            type: dataType, 
            name: $('#sensor_name').val().trim(),
            alarm_min: $('#edit_alarm_min').val() !== "" ? parseFloat($('#edit_alarm_min').val()) : null,
            relay_min: $('#edit_relay_min').val() !== "" ? parseFloat($('#edit_relay_min').val()) : null,
            relay_max: $('#edit_relay_max').val() !== "" ? parseFloat($('#edit_relay_max').val()) : null, 
            alarm_max: $('#edit_alarm_max').val() !== "" ? parseFloat($('#edit_alarm_max').val()) : null,
            location: $('#location_select').val(),
            group: $('#group_select').val(),       
            mute_until: muteUntilPayload, 
            schedules: schedulesArray 
        };

        $.ajax({
            url: `/api/settings/${sensorId}`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            success: function(response) {
                if (response.status === 'success') {
                    window.location.href = '/';
                } else {
                    alert("Ошибка изменения настроек: " + response.message);
                }
            },
            error: function(jqXHR) {
                let msg = "Критическая ошибка при сохранении настроек на сервере!";
                if (jqXHR.responseJSON && jqXHR.responseJSON.message) {
                    msg += "\nДетали: " + jqXHR.responseJSON.message;
                }
                alert(msg);
            }
        });
    });
});