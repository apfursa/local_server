const charts = {};

function getChartConfig(type, data) {
    return {
        type: 'line',
        plugins: [typeof limitLinesPlugin !== 'undefined' ? limitLinesPlugin : {}],
        data: {
            labels: data.labels,
            datasets: [{
                label: type,
                data: data.values,
                borderColor: '#000000',
                backgroundColor: 'transparent',
                fill: false,
                tension: 0.3,
                pointRadius: 0,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            customLimits: data.limits,
            scales: {
                y: {
                    ticks: { font: { size: 10 } },
                    suggestedMin: data.limits ? data.limits.min - 2 : undefined,
                    suggestedMax: data.limits ? data.limits.max + 2 : undefined
                },
                x: { ticks: { font: { size: 10 }, autoSkip: true, maxTicksLimit: 7 } }
            },
            plugins: { legend: { display: false } }
        }
    };
}

function updateChartButtons($container, sensorId, type, hours) {
    let btnHtml = '';
    [1, 24].forEach(hr => {
        const isSelected = (hours == hr);
        const style = `background: ${isSelected ? '#007bff' : '#eee'}; color: ${isSelected ? '#fff' : '#333'}; padding: 4px 10px; margin-right: 5px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em;`;
        // Используем явный вызов через window.toggleChart, чтобы не зависеть от контекстов
        btnHtml += `<button class="chart-btn" style="${style}" 
                    onclick="window.toggleChart('${sensorId}', '${type}', ${hr})">
                    ${hr === 1 ? '1 час' : '24 часа'}</button>`;
    });
    $container.html(btnHtml);
}

// Экспортируем функцию в глобальную видимость window
window.toggleChart = function(sensorId, type, hours = 24) {
    const fullId = sensorId + '_' + type;

    // Синхронизировано с id="chart-row-[%uid%]" и id="canvas-[%uid%]" в index.html
    const $chartRow = $('#chart-row-' + fullId);
    const $canvas = $('#canvas-' + fullId);

    // Если график уже открыт И нажата та же кнопка часов — закрываем строку
    if ($chartRow.is(':visible') && charts[fullId]?.lastHours === hours) {
        $chartRow.hide();
        return;
    }

    // Если закрыт или переключаем время — отображаем строку
    $chartRow.show();

    $.get(`/api/history/${sensorId}`, { type: type, hours: hours })
        .done(function(response) {
            const data = (typeof response === 'string') ? JSON.parse(response) : response;

            // Ищем или создаем контейнер для кнопок 1ч/24ч
            let $btnContainer = $('#btns-' + fullId);
            if ($btnContainer.length === 0) {
                $btnContainer = $(`<div id="btns-${fullId}" class="chart-btn-container" style="padding: 5px 10px;"></div>`);
                $canvas.parent().prepend($btnContainer);
            }

            // Перерисовываем кнопки периода
            updateChartButtons($btnContainer, sensorId, type, hours);

            // Сбрасываем старый инстанс Chart.js, если он был
            if (charts[fullId]) charts[fullId].destroy();

            // Инициализируем новый график на холсте canvas
            if ($canvas.length > 0) {
                const ctx = $canvas[0].getContext('2d');
                charts[fullId] = new Chart(ctx, getChartConfig(type, data));
                charts[fullId].lastHours = hours; // Запоминаем текущий выбор
            } else {
                console.error(`Элемент #canvas-${fullId} не найден в DOM разметке.`);
            }
        })
        .fail(() => alert("Ошибка загрузки истории"));
};