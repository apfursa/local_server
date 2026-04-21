$(document).ready(function() {
    // Вытаскиваем ID из пути: /settings/39 -> 39
    const sensorId = window.location.pathname.split('/').pop();
    if (sensorId) {
        document.title = `Настройки модуля ${sensorId}`; // Меняем <title> динамически
    }
    
    // Вытаскиваем тип из параметров: ?type=hum -> hum (по умолчанию temp)
    const urlParams = new URLSearchParams(window.location.search);
    const dataType = urlParams.get('type') || 'temp';

    // 1. ЗАГРУЗКА ДАННЫХ (GET)
    $.getJSON(`/api/settings/${sensorId}?type=${dataType}`, function(data) {
        $('#min_val').val(data.min);
        $('#max_val').val(data.max);
        $('#device_title').text(`Настройки: ${data.type} (ID ${sensorId})`);

        // ВАЖНО: используем таймаут, чтобы дать селекту отрисоваться
        setTimeout(function() {
            const typeToSet = data.ui_type || 'numeric';
            
            // Устанавливаем значение
            $('#ui_type').val(typeToSet).change(); 

            // Проверка для тебя в консоль (F12)
            if ($('#ui_type').val() !== typeToSet) {
                console.error("ОШИБКА: Список не смог выбрать " + typeToSet + ". Проверь value в HTML!");
            } else {
                console.log("Успешно установлено: " + typeToSet);
            }
        }, 10); // 100 миллисекунд хватит за глаза

        
    }).fail(function() {
        alert("Ошибка связи с сервером при загрузке!");
    });

    // 2. СОХРАНЕНИЕ ДАННЫХ (POST)
    $('#save_btn').on('click', function() {
        const payload = {
            min: $('#min_val').val(),
            max: $('#max_val').val(),
            ui_type: $('#ui_type').val()
        };

        $.ajax({
            url: `/api/settings/${sensorId}?type=${dataType}`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            success: function(response) {
                if (response.success) {
                    window.location.href = '/'; 
                } else {
                    alert("Ошибка: " + response.message);
                }
            },
            error: function() {
                alert("Критическая ошибка при сохранении!");
            }
        });
    });
});