import time
import threading

def sync_worker(app):
    """Заглушка фонового процесса синхронизации"""
    # Даем серверу Flask 5 секунд, чтобы полностью инициализироваться
    time.sleep(5)
    print("--- Фоновый поток синхронизации запущен (РЕЖИМ ЗАГЛУШКИ) ---")
    
    while True:
        # Здесь в будущем будет логика отправки Measurement.is_synced на Yii2
        # А пока просто имитируем активность раз в 10 минут
        time.sleep(600) 
        print("Синхронизация: проверка новых данных... (заглушка активна)")

def start_sync(app):
    """Запуск потока из run.py"""
    # daemon=True гарантирует, что поток умрет вместе с основным процессом Python
    thread = threading.Thread(target=sync_worker, args=(app,), daemon=True)
    thread.start()