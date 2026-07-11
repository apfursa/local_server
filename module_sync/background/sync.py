"""
Фоновый демон-синхронизатор.
Пушит локальные данные на удалённый Yii2-сервер и тянет обратно изменения.
"""

import os
import time
import json
import logging
import threading
import requests
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

LOCAL_TZ = timezone(timedelta(hours=3))

# Конфигурация
LOCAL_API = "http://127.0.0.1:80/sync"
REMOTE_URL = "https://mysmartautomation.ru"
SYNC_API_KEY = "MySm@rt2026!Kz9x"  # Ключ для авторизации
SYNC_INTERVAL = 30  # 30 секунд
LOCAL_DB = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), 'sensors.db')

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sync_state.json')


def _get_local_time():
    return datetime.now(LOCAL_TZ).strftime('%Y-%m-%d %H:%M:%S')


def _get_headers():
    headers = {'Content-Type': 'application/json'}
    if SYNC_API_KEY:
        headers['X-Sync-Key'] = SYNC_API_KEY
    return headers


def _load_state():
    import os
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'last_sync_time': '1970-01-01 00:00:00'}


def _save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def _push_data():
    """Собрать данные из SQLite и отправить на удалённый сервер."""
    try:
        # Получаем несинхронизированные measurements
        resp = requests.get(f"{LOCAL_API}/get-unsynced", timeout=10)
        measurements = resp.json() if resp.status_code == 200 else []

        # Получаем все остальные данные (settings, schedules, categories, system_settings)
        # Через pull endpoint локального сервера с since=0
        all_data_resp = requests.get(f"{LOCAL_API}/pull", params={'since': ''}, timeout=10)
        all_data = all_data_resp.json() if all_data_resp.status_code == 200 else {}

        payload = {}

        # Устройства — напрямую из SQLite
        try:
            import sqlite3
            db_path = os.path.abspath(LOCAL_DB)
            conn = sqlite3.connect(db_path)
            cursor = conn.execute('SELECT id, name, last_seen FROM devices')
            devices = [{'id': r[0], 'name': r[1], 'last_seen': str(r[2]) if r[2] else ''} for r in cursor.fetchall()]
            conn.close()
            if devices:
                payload['devices'] = devices
        except Exception as e:
            logging.warning(f'[{_get_local_time()}] Push: не удалось прочитать devices: {e}')

        if measurements:
            payload['measurements'] = [
                {'sensor_id': m['sensor_id'], 'value': m['value'],
                 'data_type': m['type'], 'timestamp': m['timestamp']}
                for m in measurements
            ]

        for key in ['settings', 'schedules', 'categories', 'system_settings']:
            items = all_data.get(key, [])
            if items:
                payload[key] = items

        if not payload:
            logging.info(f'[{_get_local_time()}] Push: нет данных для отправки')
            return

        logging.info(f'[{_get_local_time()}] Push: отправляю {list(payload.keys())}')

        resp = requests.post(
            f"{REMOTE_URL}/api/sync/push",
            headers=_get_headers(),
            data=json.dumps(payload),
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()

        # Подтверждаем measurements
        if measurements:
            uploaded_ids = [m['id'] for m in measurements]
            requests.post(
                f"{LOCAL_API}/confirm",
                json={"ids": uploaded_ids},
                timeout=5,
            )

        logging.info(f'[{_get_local_time()}] Push: {result.get("synced", {})}')

    except Exception as e:
        logging.error(f'[{_get_local_time()}] Push ERROR: {e}')


def _pull_data(last_sync_time):
    """Получить изменения с удалённого сервера и применить к SQLite."""
    try:
        resp = requests.get(
            f"{REMOTE_URL}/api/sync/pull",
            headers=_get_headers(),
            params={'since': last_sync_time},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logging.error(f'[{_get_local_time()}] Pull ERROR: {e}')
        return last_sync_time

    if not data:
        logging.info(f'[{_get_local_time()}] Pull: нет изменений')
        return last_sync_time

    # Извлечь время сервера ДО отправки данных
    server_time = data.pop('_server_time', None)

    # Отправляем данные на локальный сервер для применения
    resp = requests.post(
        f"{LOCAL_API}/push",
        json=data,
        timeout=30,
    )

    # Обновить device.last_seen временем удалённого сервера
    if server_time:
        try:
            import sqlite3
            db_path = os.path.abspath(LOCAL_DB)
            logging.info(f'[{_get_local_time()}] Pull: DB path = {db_path}')
            conn = sqlite3.connect(db_path)
            conn.execute('UPDATE devices SET last_seen = ?', (server_time,))
            conn.commit()
            conn.close()
            logging.info(f'[{_get_local_time()}] Pull: last_seen обновлён на {server_time}')
        except Exception as e:
            logging.warning(f'[{_get_local_time()}] Pull: не удалось обновить last_seen: {e}')

    max_time = last_sync_time
    for key in ['settings', 'schedules', 'categories', 'system_settings']:
        for item in data.get(key, []):
            t = item.get('updated_at', '')
            if t and t > max_time:
                max_time = t

    counts = {k: len(v) for k, v in data.items()}
    logging.info(f'[{_get_local_time()}] Pull: {counts}')

    return max_time


def _sync_worker():
    """Основной цикл синхронизации."""
    time.sleep(5)
    logging.info("[SYNC] Фоновый синхронизатор запущен.")

    state = _load_state()

    while True:
        try:
            # Push: локальные данные → удалённый сервер
            _push_data()

            # Pull: удалённые изменения → локальная БД
            new_time = _pull_data(state['last_sync_time'])
            state['last_sync_time'] = new_time
            _save_state(state)

        except Exception as err:
            logging.error(f'[{_get_local_time()}] Ошибка цикла: {err}')

        time.sleep(SYNC_INTERVAL)


def start_sync():
    """Запускает фоновый поток синхронизации."""
    sync_thread = threading.Thread(target=_sync_worker, daemon=True)
    sync_thread.start()
