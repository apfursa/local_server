"""
Фоновый демон-синхронизатор.
Периодически просыпается, забирает локальный буфер и пушит его на внешний сервер в интернете.
"""

import time
import logging
import threading
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Конфигурация путей
LOCAL_API_GET = "http://127.0.0.1:5000/api/sync/get-unsynced"
LOCAL_API_CONFIRM = "http://127.0.0.1:5000/api/sync/confirm"
REMOTE_CLOUD_API = "http://api.apinjener.ru/v1/backload"


def _sync_worker():
    """Внутренний бесконечный цикл синхронизации."""
    # Даем основному веб-серверу Flask 5 секунд на запуск и инициализацию порта
    time.sleep(5)
    logging.info("[SYNC] Фоновый синхронизатор облака успешно запущен.")

    while True:
        try:
            # Шаг 1: Стучимся к своему локальному роуту за пачкой несинхронизированных данных
            response = requests.get(LOCAL_API_GET, timeout=5)
            if response.status_code != 200:
                time.sleep(60)
                continue

            unsynced_data = response.json()

            # Если буфер пуст — отдыхаем 1 минуту
            if not unsynced_data:
                time.sleep(60)
                continue

            logging.info(f"[SYNC] Найдено {len(unsynced_data)} записей для отправки в интернет...")

            # Шаг 2: Шлем эту пачку на твой удаленный сервер в интернете
            # (Таймаут 10 сек на случай плохой связи через 4G)
            cloud_resp = requests.post(REMOTE_CLOUD_API, json=unsynced_data, timeout=10)

            # Шаг 3: Если облако подтвердило прием кодом 200
            if cloud_resp.status_code == 200:
                # Собираем массив ID, которые мы только что успешно выгрузили
                uploaded_ids = [item['id'] for item in unsynced_data]

                # Шлем массив обратно локальному контроллеру для закрытия флагов
                confirm_resp = requests.post(LOCAL_API_CONFIRM, json={"ids": uploaded_ids}, timeout=5)

                if confirm_resp.status_code == 200:
                    logging.info(f"[SYNC] Успех! Пачка из {len(uploaded_ids)} записей зафиксирована в облаке.")
                else:
                    logging.error("[SYNC] Локальный сервер отказался подтвердить закрытие флагов.")
            else:
                logging.warn(f"[SYNC] Интернет-сервер вернул ошибку {cloud_resp.status_code}. Повтор через минуту.")

        except requests.exceptions.RequestException as net_err:
            # Сюда мы прилетим, если оборвется связь с интернетом. Ничего не падает, просто ждем.
            logging.warn(f"[SYNC] Сетевой сбой при отправке в облако (проверьте 4G): {net_err}")
        except Exception as err:
            logging.error(f"[SYNC] Непредвиденная ошибка потока: {err}")

        # Засыпаем на 1 минуту до следующей проверки буфера
        time.sleep(60)


def start_sync():
    """Запускает независимый фоновый поток выгрузки истории."""
    sync_thread = threading.Thread(target=_sync_worker, daemon=True)
    sync_thread.start()