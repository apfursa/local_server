#!/usr/bin/env python3
"""
Синхронизация данных с удалённым сервером (Yii2 + MySQL).
Запуск через cron каждые 5 минут:
*/5 * * * * /usr/bin/python3 /path/to/sync_to_remote.py >> /var/log/sync.log 2>&1
"""

import sqlite3
import requests
import json
import os
from datetime import datetime, timezone, timedelta

# ============ КОНФИГУРАЦИЯ ============

REMOTE_URL = os.environ.get('SYNC_REMOTE_URL', 'https://mysmartautomation.ru')
API_KEY = os.environ.get('SYNC_API_KEY', 'MySm@rt2026!Kz9x')
LOCAL_DB = os.environ.get('SYNC_LOCAL_DB', '/var/lib/sqlite/mysmartautomation.db')
SYNC_STATE_FILE = os.environ.get('SYNC_STATE_FILE', '/var/lib/sqlite/sync_state.json')

LOCAL_TZ = timezone(timedelta(hours=3))  # Europe/Moscow

# ============ КОНЕЦ КОНФИГУРАЦИИ ============


def get_local_time():
    """Текущее время в местном timezone."""
    return datetime.now(LOCAL_TZ).strftime('%Y-%m-%d %H:%M:%S')


def load_sync_state():
    """Загрузить состояние синхронизации."""
    if os.path.exists(SYNC_STATE_FILE):
        with open(SYNC_STATE_FILE, 'r') as f:
            return json.load(f)
    return {'last_sync_time': '1970-01-01 00:00:00'}


def save_sync_state(state):
    """Сохранить состояние синхронизации."""
    os.makedirs(os.path.dirname(SYNC_STATE_FILE), exist_ok=True)
    with open(SYNC_STATE_FILE, 'w') as f:
        json.dump(state, f)


def get_headers():
    """Заголовки для API-запросов."""
    headers = {'Content-Type': 'application/json'}
    if API_KEY:
        headers['X-Sync-Key'] = API_KEY
    return headers


def push_data(conn):
    """Отправить данные с локального сервера на удалённый."""
    cursor = conn.cursor()
    payload = {}

    # Measurements (только несинхронизированные)
    cursor.execute('''
        SELECT sensor_id, value, data_type, timestamp
        FROM measurements
        WHERE is_synced = 0
        LIMIT 500
    ''')
    rows = cursor.fetchall()
    if rows:
        payload['measurements'] = [
            {'sensor_id': r[0], 'value': r[1], 'data_type': r[2], 'timestamp': r[3]}
            for r in rows
        ]

    # Devices
    cursor.execute('SELECT id, name, last_seen FROM device')
    rows = cursor.fetchall()
    if rows:
        payload['devices'] = [
            {'id': r[0], 'name': r[1], 'last_seen': r[2]}
            for r in rows
        ]

    # Settings
    cursor.execute('''
        SELECT sensor_id, data_type, name, ui_type, location_id, group_id,
               alarm_min, relay_min, relay_max, alarm_max,
               offline_timeout, mute_until, sort_order, is_deleted, updated_at
        FROM settings
    ''')
    rows = cursor.fetchall()
    if rows:
        payload['settings'] = [
            {
                'sensor_id': r[0], 'data_type': r[1], 'name': r[2],
                'ui_type': r[3], 'location_id': r[4], 'group_id': r[5],
                'alarm_min': r[6], 'relay_min': r[7], 'relay_max': r[8],
                'alarm_max': r[9], 'offline_timeout': r[10],
                'mute_until': r[11], 'sort_order': r[12], 'is_deleted': r[13],
                'updated_at': r[14],
            }
            for r in rows
        ]

    # Schedules
    cursor.execute('''
        SELECT id, sensor_id, data_type, time_start, time_end,
               alarm_min, relay_min, relay_max, alarm_max, updated_at
        FROM device_schedules
    ''')
    rows = cursor.fetchall()
    if rows:
        payload['schedules'] = [
            {
                'id': r[0], 'sensor_id': r[1], 'data_type': r[2],
                'time_start': r[3], 'time_end': r[4],
                'alarm_min': r[5], 'relay_min': r[6], 'relay_max': r[7],
                'alarm_max': r[8], 'updated_at': r[9],
            }
            for r in rows
        ]

    # Categories
    cursor.execute('SELECT id, name, type, updated_at FROM categories')
    rows = cursor.fetchall()
    if rows:
        payload['categories'] = [
            {'id': r[0], 'name': r[1], 'type': r[2], 'updated_at': r[3]}
            for r in rows
        ]

    # System settings
    cursor.execute('''
        SELECT key, value, data_type, name, description, updated_at
        FROM system_settings
    ''')
    rows = cursor.fetchall()
    if rows:
        payload['system_settings'] = [
            {
                'key': r[0], 'value': r[1], 'data_type': r[2],
                'name': r[3], 'description': r[4], 'updated_at': r[5],
            }
            for r in rows
        ]

    if not payload:
        print(f'[{get_local_time()}] Push: нет данных для отправки')
        return

    try:
        resp = requests.post(
            f'{REMOTE_URL}/api/sync/push',
            headers=get_headers(),
            data=json.dumps(payload),
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()

        # Пометить measurements как синхронизированные
        if payload.get('measurements'):
            synced_ids = []
            for m in payload['measurements']:
                cursor.execute(
                    'SELECT id FROM measurements WHERE sensor_id=? AND data_type=? AND timestamp=?',
                    (m['sensor_id'], m['data_type'], m['timestamp'])
                )
                row = cursor.fetchone()
                if row:
                    synced_ids.append(row[0])

            if synced_ids:
                placeholders = ','.join(['?'] * len(synced_ids))
                cursor.execute(f'UPDATE measurements SET is_synced=1 WHERE id IN ({placeholders})', synced_ids)
                conn.commit()

        print(f'[{get_local_time()}] Push: {result.get("synced", {})}')

    except Exception as e:
        print(f'[{get_local_time()}] Push ERROR: {e}')


def pull_data(conn, last_sync_time):
    """Получить изменения с удалённого сервера."""
    try:
        resp = requests.get(
            f'{REMOTE_URL}/api/sync/pull',
            headers=get_headers(),
            params={'since': last_sync_time},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f'[{get_local_time()}] Pull ERROR: {e}')
        return last_sync_time

    if not data:
        print(f'[{get_local_time()}] Pull: нет изменений')
        return last_sync_time

    cursor = conn.cursor()
    max_time = last_sync_time

    # Settings
    for s in data.get('settings', []):
        remote_time = s['updated_at']
        if remote_time > max_time:
            max_time = remote_time

        cursor.execute(
            'SELECT updated_at FROM settings WHERE sensor_id=? AND data_type=?',
            (s['sensor_id'], s['data_type'])
        )
        existing = cursor.fetchone()

        if not existing or remote_time > (existing[0] or '0000-00-00 00:00:00'):
            cursor.execute('''
                INSERT OR REPLACE INTO settings
                (sensor_id, data_type, name, ui_type, location_id, group_id,
                 alarm_min, relay_min, relay_max, alarm_max,
                 offline_timeout, mute_until, sort_order, is_deleted, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                s['sensor_id'], s['data_type'], s.get('name'),
                s.get('ui_type', 'numeric'), s.get('location_id'),
                s.get('group_id'), s.get('alarm_min'), s.get('relay_min'),
                s.get('relay_max'), s.get('alarm_max'),
                s.get('offline_timeout', 5), s.get('mute_until'),
                s.get('sort_order', 0), s.get('is_deleted', 0),
                remote_time,
            ))

    # Schedules
    for sc in data.get('schedules', []):
        remote_time = sc['updated_at']
        if remote_time > max_time:
            max_time = remote_time

        cursor.execute('SELECT updated_at FROM device_schedules WHERE id=?', (sc['id'],))
        existing = cursor.fetchone()

        if not existing or remote_time > (existing[0] or '0000-00-00 00:00:00'):
            cursor.execute('''
                INSERT OR REPLACE INTO device_schedules
                (id, sensor_id, data_type, time_start, time_end,
                 alarm_min, relay_min, relay_max, alarm_max, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sc['id'], sc['sensor_id'], sc['data_type'],
                sc['time_start'], sc['time_end'],
                sc.get('alarm_min'), sc.get('relay_min'),
                sc.get('relay_max'), sc.get('alarm_max'),
                remote_time,
            ))

    # Categories
    for c in data.get('categories', []):
        remote_time = c['updated_at']
        if remote_time > max_time:
            max_time = remote_time

        cursor.execute('SELECT updated_at FROM categories WHERE id=?', (c['id'],))
        existing = cursor.fetchone()

        if not existing or remote_time > (existing[0] or '0000-00-00 00:00:00'):
            cursor.execute('''
                INSERT OR REPLACE INTO categories (id, name, type, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (c['id'], c['name'], c['type'], remote_time))

    # System settings
    for ss in data.get('system_settings', []):
        remote_time = ss['updated_at']
        if remote_time > max_time:
            max_time = remote_time

        cursor.execute('SELECT updated_at FROM system_settings WHERE key=?', (ss['key'],))
        existing = cursor.fetchone()

        if not existing or remote_time > (existing[0] or '0000-00-00 00:00:00'):
            cursor.execute('''
                INSERT OR REPLACE INTO system_settings
                (key, value, data_type, name, description, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ss['key'], ss['value'], ss.get('data_type', 'string'),
                  ss.get('name'), ss.get('description'), remote_time))

    conn.commit()

    counts = {k: len(v) for k, v in data.items()}
    print(f'[{get_local_time()}] Pull: {counts}')

    return max_time


def main():
    print(f'[{get_local_time()}] === Синхронизация начата ===')

    conn = sqlite3.connect(LOCAL_DB)
    state = load_sync_state()

    # Push: локальные данные → удалённый сервер
    push_data(conn)

    # Pull: удалённые изменения → локальная БД
    new_time = pull_data(conn, state['last_sync_time'])
    state['last_sync_time'] = new_time
    save_sync_state(state)

    conn.close()
    print(f'[{get_local_time()}] === Синхронизация завершена ===\n')


if __name__ == '__main__':
    main()
