from flask import Blueprint, jsonify, request, redirect
# from models.device import Device
from models.setting import Setting
from core.db_config import db

# Создаем Blueprint для настроек
settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/rename', methods=['POST'])
def rename_device():
    sid = request.form.get('sensor_id')
    new_name = request.form.get('new_name')
    d_type = request.form.get('sensor_type', 'temp')

    print(f"Пытаюсь переименовать: ID={sid}, Type={d_type}, Name={new_name}")
    
    # Добавляем проверку d_type
    if sid and new_name and d_type:
        setting = Setting.query.filter_by(sensor_id=int(sid), data_type=d_type).first()
        
        if not setting:
            print(f"Создаю новую запись для {sid} [{d_type}]")
            setting = Setting(sensor_id=int(sid), data_type=d_type)
            db.session.add(setting)
        
        setting.name = new_name
        db.session.commit()
        print(f"Успешно сохранено в БД: {new_name}")
    else:
        print("Ошибка: Не все данные получены из формы (проверь disabled/readOnly)")
            
    return redirect('/')

@settings_bp.route('/api/settings/<int:sensor_id>', methods=['GET', 'POST'])
def handle_settings(sensor_id):
    """Универсальное API для работы с порогами и типом иконки (ui_type)"""
    
    # 1. Определяем тип данных из параметров запроса
    d_type = request.args.get('type', default='temp')
    
    # 2. Ищем существующую запись в базе
    setting = Setting.query.filter_by(sensor_id=sensor_id, data_type=d_type).first()
    
    # --- ОБРАБОТКА СОХРАНЕНИЯ (POST) ---
    if request.method == 'POST':
        data = request.get_json()
        
        # Если записи еще нет — создаем её
        if not setting:
            setting = Setting(sensor_id=sensor_id, data_type=d_type)
            db.session.add(setting)
        
        # Обновляем поля из пришедшего JSON
        setting.ui_type = data.get('ui_type', 'numeric')
        
        try:
            new_min = float(data.get('min', 18.0))
            new_max = float(data.get('max', 28.0))
            
            # Сохраняем границы через метод модели (проверка логики min < max)
            success, message = setting.set_bounds(new_min, new_max)
            
            if success:
                db.session.commit() # Фиксируем изменения (включая ui_type) в БД
                
            return jsonify({'success': success, 'message': message})
            
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Некорректный формат чисел'})

    # --- ОБРАБОТКА ПОЛУЧЕНИЯ ДАННЫХ (GET) ---
    # Важно: здесь только ОДИН return, который содержит все поля
    return jsonify({
        'min': setting.min if setting else 18.0,
        'max': setting.max if setting else 28.0,
        'ui_type': setting.ui_type if setting else 'numeric',
        'type': d_type
    })