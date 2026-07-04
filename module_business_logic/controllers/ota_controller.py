"""
OTA контроллер — управление прошивками устройств.
Путь: D:\Moy_Server\module_business_logic\controllers\ota_controller.py

Эндпоинты:
  POST /api/ota/check              — ESP проверяет наличие обновления
  GET  /api/ota/firmware/<id>      — ESP скачивает активную прошивку
  POST /api/ota/upload             — загрузка новой прошивки на сервер
  POST /api/ota/activate/<fw_id>   — активировать версию (для отката)
  GET  /api/ota/list               — список всех прошивок
  POST /api/ota/delete/<fw_id>     — удалить версию из архива
"""

import os
from datetime import datetime
from flask import Blueprint, jsonify, request, send_from_directory
from module_data_layer.core.db_config import db
from module_data_layer.models.firmware import Firmware

ota_bp = Blueprint('ota', __name__)

# Папка где хранятся .bin файлы
FIRMWARE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'firmware')
)


def get_firmware_dir():
    """Возвращает абсолютный путь к папке с прошивками, создаёт если нет."""
    os.makedirs(FIRMWARE_DIR, exist_ok=True)
    return FIRMWARE_DIR


# ---------------------------------------------------------------
# POST /api/ota/check
# Тело: {"sensor_id": 39, "version": 3}
# Ответ если есть обновление: {"update": true, "version": 4, "url": "..."}
# Ответ если нет: {"update": false}
# ---------------------------------------------------------------
@ota_bp.route('/check', methods=['POST'])
def check_update():
    data = request.get_json(silent=True)
    if not data or 'sensor_id' not in data or 'version' not in data:
        return jsonify({"error": "sensor_id and version required"}), 400

    sensor_id = int(data['sensor_id'])
    current_version = int(data['version'])

    # Ищем активную прошивку для этого устройства
    firmware = db.session.query(Firmware).filter_by(
        sensor_id=sensor_id, is_active=1
    ).first()

    if not firmware:
        print(f"[OTA] Активная прошивка для sensor_id={sensor_id} не найдена")
        return jsonify({"update": False})

    if firmware.version != current_version:
        host = request.host
        url = f"http://{host}/api/ota/firmware/{sensor_id}"

        print(f"[OTA] Обновление для sensor_id={sensor_id}: "
              f"v{current_version} → v{firmware.version}")

        return jsonify({
            "update": True,
            "version": firmware.version,
            "url": url
        })

    print(f"[OTA] sensor_id={sensor_id} уже на актуальной версии v{current_version}")
    return jsonify({"update": False})


# ---------------------------------------------------------------
# GET /api/ota/firmware/<sensor_id>
# ESP скачивает активный .bin файл
# ---------------------------------------------------------------
@ota_bp.route('/firmware/<int:sensor_id>', methods=['GET'])
def download_firmware(sensor_id):
    firmware = db.session.query(Firmware).filter_by(
        sensor_id=sensor_id, is_active=1
    ).first()

    if not firmware:
        return jsonify({"error": "Active firmware not found"}), 404

    firmware_dir = get_firmware_dir()
    filepath = os.path.join(firmware_dir, firmware.filename)

    if not os.path.exists(filepath):
        print(f"[OTA] Файл не найден: {filepath}")
        return jsonify({"error": "File not found on server"}), 404

    print(f"[OTA] Отдаём прошивку: {firmware.filename} для sensor_id={sensor_id}")
    return send_from_directory(firmware_dir, firmware.filename,
                               as_attachment=True,
                               mimetype='application/octet-stream')


# ---------------------------------------------------------------
# POST /api/ota/upload
# Form-data: sensor_id, version, file (.bin), description (опционально)
# Новая прошивка автоматически становится активной
# ---------------------------------------------------------------
@ota_bp.route('/upload', methods=['POST'])
def upload_firmware():
    sensor_id = request.form.get('sensor_id')
    version = request.form.get('version')
    description = request.form.get('description', '')
    file = request.files.get('file')

    if not sensor_id or not version or not file:
        return jsonify({"error": "sensor_id, version and file required"}), 400

    if not file.filename.endswith('.bin'):
        return jsonify({"error": "Only .bin files allowed"}), 400

    sensor_id = int(sensor_id)
    version = int(version)

    # Проверяем что такой версии ещё нет
    existing = db.session.query(Firmware).filter_by(
        sensor_id=sensor_id, version=version
    ).first()
    if existing:
        return jsonify({"error": f"Version {version} already exists"}), 400

    # Сохраняем файл
    filename = f"sensor{sensor_id}_v{version}.bin"
    firmware_dir = get_firmware_dir()
    filepath = os.path.join(firmware_dir, filename)
    file.save(filepath)

    # Снимаем активность со всех предыдущих версий этого устройства
    db.session.query(Firmware).filter_by(sensor_id=sensor_id).update({"is_active": 0})

    # Создаём новую запись и делаем её активной
    firmware = Firmware(
        sensor_id=sensor_id,
        version=version,
        filename=filename,
        description=description,
        is_active=1  # новая версия сразу активна
    )
    db.session.add(firmware)
    db.session.commit()

    print(f"[OTA] Загружена прошивка: {filename} v{version} для sensor_id={sensor_id}")
    return jsonify({
        "status": "ok",
        "sensor_id": sensor_id,
        "version": version,
        "filename": filename
    })


# ---------------------------------------------------------------
# POST /api/ota/activate/<fw_id>
# Активировать конкретную версию (для отката или переключения)
# ---------------------------------------------------------------
@ota_bp.route('/activate/<int:fw_id>', methods=['POST'])
def activate_firmware(fw_id):
    firmware = db.session.query(Firmware).filter_by(id=fw_id).first()
    if not firmware:
        return jsonify({"error": "Firmware not found"}), 404

    # Проверяем что файл реально существует
    firmware_dir = get_firmware_dir()
    if not os.path.exists(os.path.join(firmware_dir, firmware.filename)):
        return jsonify({"error": "File not found on server"}), 404

    # Снимаем активность со всех версий этого устройства
    db.session.query(Firmware).filter_by(sensor_id=firmware.sensor_id).update({"is_active": 0})

    # Активируем выбранную версию
    firmware.is_active = 1
    db.session.commit()

    print(f"[OTA] Активирована прошивка v{firmware.version} для sensor_id={firmware.sensor_id}")
    return jsonify({
        "status": "ok",
        "sensor_id": firmware.sensor_id,
        "version": firmware.version
    })


# ---------------------------------------------------------------
# POST /api/ota/delete/<fw_id>
# Удалить версию из архива (нельзя удалить активную)
# ---------------------------------------------------------------
@ota_bp.route('/delete/<int:fw_id>', methods=['POST'])
def delete_firmware(fw_id):
    firmware = db.session.query(Firmware).filter_by(id=fw_id).first()
    if not firmware:
        return jsonify({"error": "Firmware not found"}), 404

    if firmware.is_active:
        return jsonify({"error": "Cannot delete active firmware"}), 400

    # Удаляем файл с диска
    firmware_dir = get_firmware_dir()
    filepath = os.path.join(firmware_dir, firmware.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(firmware)
    db.session.commit()

    print(f"[OTA] Удалена прошивка v{firmware.version} для sensor_id={firmware.sensor_id}")
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------
# GET /api/ota/list
# Список всех прошивок сгруппированных по sensor_id
# ---------------------------------------------------------------
@ota_bp.route('/list', methods=['GET'])
def list_firmware():
    firmwares = db.session.query(Firmware).order_by(
        Firmware.sensor_id, Firmware.version.desc()
    ).all()

    firmware_dir = get_firmware_dir()
    result = []
    for f in firmwares:
        result.append({
            "id": f.id,
            "sensor_id": f.sensor_id,
            "version": f.version,
            "filename": f.filename,
            "uploaded_at": f.uploaded_at.strftime('%d.%m.%Y %H:%M'),
            "description": f.description or '',
            "is_active": f.is_active,
            "file_exists": os.path.exists(os.path.join(firmware_dir, f.filename))
        })
    return jsonify(result)
