const charts = {};

function getChartConfig(type, data) {
    return {
        type: 'line',
        plugins: [limitLinesPlugin],
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
        const style = `background: ${isSelected ? '#007bff' : '#eee'}; color: ${isSelected ? '#fff' : '#333'};`;
        btnHtml += `<button class="chart-btn" style="${style}" 
                    onclick="toggleChart('${sensorId}', '${type}', ${hr})">
                    ${hr === 1 ? '1 час' : '24 часа'}</button>`;
    });
    $container.html(btnHtml);
}

// function toggleChart(sensorId, type, hours = 24) {
//     const fullId = sensorId + '_' + type; 
//     const $chartRow = $('#chart-row-' + fullId);
//     const $canvas = $('#canvas-' + fullId);

//     // ИСПРАВЛЕНО: $chartRow вместо $row
//     if ($chartRow.is(':visible') && charts[fullId]?.lastHours === hours) {
//         $chartRow.hide();
//         return;
//     }

//     $chartRow.show();

//     $.get(`/api/history/${sensorId}`, { type: type, hours: hours })
//         .done(function(response) {
//             const data = (typeof response === 'string') ? JSON.parse(response) : response;

//             let $btnContainer = $('#btns-' + fullId);
//             if ($btnContainer.length === 0) {
//                 $btnContainer = $(`<div id="btns-${fullId}" class="chart-btn-container"></div>`);
//                 $canvas.parent().prepend($btnContainer);
//             }
//             updateChartButtons($btnContainer, sensorId, type, hours);

//             if (charts[fullId]) charts[fullId].destroy();
            
//             const ctx = $canvas[0].getContext('2d');
//             charts[fullId] = new Chart(ctx, getChartConfig(type, data));
//             charts[fullId].lastHours = hours;
//         })
//         .fail(() => alert("Ошибка загрузки данных"));
// }

function toggleChart(sensorId, type, hours = 24) {
    const fullId = sensorId + '_' + type; 
    const $chartRow = $('#chart-row-' + fullId);
    const $canvas = $('#canvas-' + fullId);

    // Если график уже открыт И мы нажали на ту же самую кнопку (те же часы) — закрываем
    if ($chartRow.is(':visible') && charts[fullId]?.lastHours === hours) {
        $chartRow.hide();
        return;
    }

    // Если график закрыт или мы переключаем время (1ч <-> 24ч) — показываем/обновляем
    $chartRow.show();

    $.get(`/api/history/${sensorId}`, { type: type, hours: hours })
        .done(function(response) {
            const data = (typeof response === 'string') ? JSON.parse(response) : response;

            // Контейнер для кнопок
            let $btnContainer = $('#btns-' + fullId);
            if ($btnContainer.length === 0) {
                $btnContainer = $(`<div id="btns-${fullId}" class="chart-btn-container"></div>`);
                $canvas.parent().prepend($btnContainer);
            }
            
            // Обновляем кнопки (подсветка активной)
            updateChartButtons($btnContainer, sensorId, type, hours);

            // Перерисовываем график
            if (charts[fullId]) charts[fullId].destroy();
            
            const ctx = $canvas[0].getContext('2d');
            charts[fullId] = new Chart(ctx, getChartConfig(type, data));
            charts[fullId].lastHours = hours; // Запоминаем текущий режим
        })
        .fail(() => alert("Ошибка загрузки истории"));
}