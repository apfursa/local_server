$(document).ready(function() {
    let localCachedData = [];

    // Простая встроенная функция компиляции шаблонов (заменяет [%ключ%] на значение)
    function compileTemplate(templateId, data) {
        let html = $(templateId).html();
        for (let key in data) {
            let reg = new RegExp('\\[%' + key + '%\\]', 'g');
            html = html.replace(reg, data[key] !== null ? data[key] : '');
        }
        return html;
    }

    // Функция обновления стрелок (первая строка не имеет "Вверх", последняя - "Вниз")
    function updateArrowsVisibility() {
        const $rows = $('.table-sort-body-target .sort-item-row');
        $rows.each(function(index) {
            const $row = $(this);
            const $upCell = $row.find('.cell-up-action');
            const $downCell = $row.find('.cell-down-action');

            // Сбрасываем блокирующие классы и возвращаем кнопки, если они были скрыты
            $upCell.removeClass('cell-sort-disabled');
            $downCell.removeClass('cell-sort-disabled');
            
            if ($upCell.find('.btn-sort-up').length === 0 && index !== 0) {
                $upCell.html('<button class="btn-sort-action btn-sort-up">▲</button>');
            }
            if ($downCell.find('.btn-sort-down').length === 0 && index !== $rows.length - 1) {
                $downCell.html('<button class="btn-sort-action btn-sort-down">▼</button>');
            }

            // Применяем правила для первой и последней строки
            if (index === 0) {
                $upCell.addClass('cell-sort-disabled').empty();
            }
            if (index === $rows.length - 1) {
                $downCell.addClass('cell-sort-disabled').empty();
            }
        });
    }

    // 1. Загружаем актуальное состояние датчиков из общего API системы
    $.getJSON('/api/latest', function(data) {
        if (!data || data.length === 0) {
            $('#sort_table_container').html('<div style="padding:15px; text-align:center;">Датчики не найдены</div>');
            return;
        }

        localCachedData = data;

        // 2. Рендерим каркас таблицы
        const sortLayoutHtml = compileTemplate('#template-sort-layout', {});
        $('#sort_table_container').html(sortLayoutHtml);
        const $tbody = $('.table-sort-body-target');

        // 3. В цикле генерируем строки
        localCachedData.forEach((sensor, index) => {
            let btnUp = '<button class="btn-sort-action btn-sort-up">▲</button>';
            let btnDown = '<button class="btn-sort-action btn-sort-down">▼</button>';

            const rowData = $.extend({}, sensor, {
                btn_up: btnUp,
                btn_down: btnDown,
                is_relay: sensor.is_relay ? 'true' : 'false'
            });

            const $row = $(compileTemplate('#template-sort-row', rowData));
            $tbody.append($row);
        });

        // Корректируем видимость стрелок после первой сборки
        updateArrowsVisibility();
    }).fail(function() {
        $('#sort_table_container').html('<div style="padding:15px; text-align:center; color:red;">Ошибка загрузки данных</div>');
    });

    // 4. Обработка клика "ВВЕРХ"
    $(document).on('click', '.btn-sort-up', function() {
        const $currentRow = $(this).closest('.sort-item-row');
        const $prevRow = $currentRow.prev('.sort-item-row');

        if ($prevRow.length > 0) {
            $currentRow.insertBefore($prevRow);
            updateArrowsVisibility();
        }
    });

    // 5. Обработка клика "ВНИЗ"
    $(document).on('click', '.btn-sort-down', function() {
        const $currentRow = $(this).closest('.sort-item-row');
        const $nextRow = $currentRow.next('.sort-item-row');

        if ($nextRow.length > 0) {
            $currentRow.insertAfter($nextRow);
            updateArrowsVisibility();
        }
    });

    // 6. Сохранение нового порядка на сервер
    $('#save_btn').on('click', function() {
        const sortedArray = [];

        // Обходим строки таблицы в их текущем (новом) порядке и собираем ID и типы
        $('.table-sort-body-target .sort-item-row').each(function() {
            sortedArray.push({
                sensor_id: parseInt($(this).data('sensor-id')),
                type: $(this).data('type'),
                is_relay: $(this).data('is-relay') === true || $(this).data('is-relay') === 'true'
            });
        });

        if (sortedArray.length === 0) {
            alert('Нет данных для сохранения');
            return;
        }

        // Отправляем массив на наш новый единый эндпоинт контроллера sort
        $.ajax({
            url: '/sort/save',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(sortedArray),
            success: function(response) {
                if (response.status === 'success') {
                    // alert('Порядок отображения успешно сохранен!');
                    window.location.href = '/';
                } else {
                    alert('Ошибка сервера: ' + response.message);
                }
            },
            error: function() {
                alert('Критическая ошибка при сохранении порядка!');
            }
        });
    });
});