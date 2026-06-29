$(document).ready(function() {
    // 1. Загружаем текущий сохраненный номер телефона при старте страницы
    $.getJSON('/phone/api', function(data) {
        if (data && data.value) {
            $('#global_phone').val(data.value);
        } else {
            $('#global_phone').val('').attr('placeholder', 'Не задан! Введите +7...');
        }
    }).fail(function() {
        console.error("Не удалось загрузить номер телефона с сервера.");
    });

    // 2. Сохранение номера по клику на верхнюю кнопку панели
    $('#save_btn').on('click', function() {
        const phoneValue = $('#global_phone').val().trim();

        // Валидация на стороне клиента
        if (phoneValue === "") {
            alert('Поле номера не может быть пустым!');
            return;
        }

        if (!phoneValue.startsWith('+')) {
            alert('Номер должен начинаться с плюса и содержать код страны (например, +7...)');
            return;
        }

        // Отправка данных на бэкенд
        $.ajax({
            url: '/phone/api',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ value: phoneValue }),
            success: function(response) {
                if (response.status === 'success') {
                    // alert('Номер успешно сохранен!');
                    window.location.href = '/';
                } else {
                    alert('Ошибка сервера: ' + response.message);
                }
            },
            error: function() {
                alert('Критическая ошибка при сохранении номера!');
            }
        });
    });
});