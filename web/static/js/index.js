function refreshData() {
    $.getJSON('/api/latest', function(data) {
        let $tbody = $('#table-body');
        $.each(data, function(index, sensor) {
            let $row = $('#row-' + sensor.id + '_' + sensor.type);
            
            if ($row.length === 0) {
                $tbody.append(createRow(sensor));
            } else {
                // ТУТ ВАЖНО: обновляем значение через нашу функцию
                let displayValue = getDisplayValue(sensor.value, sensor.ui_type);
                $row.find('[data-field="value"]').text(displayValue).css('color', sensor.color);
                $row.find('[data-field="time"]').text(sensor.time);
            }
        });
    });
}

$(document).ready(function() {
    refreshData();
    setInterval(refreshData, 30000);
});