import requests
import json
import time

# 1. НАСТРОЙКИ
SERVER_URL = "http://127.0.0.1"
MODUL_ID   = 65

# Два реле на одном модуле
RELAYS = [
    {"relay_pin": "D1", "state": 0},  # реле 1 — изначально выкл
    {"relay_pin": "D2", "state": 0},  # реле 2 — изначально выкл
]

SEND_INTERVAL = 10  # секунд (для теста — 10, в реале — 60)


def check_relay(relay_pin, current_state):
    """Отправляет запрос на сервер и получает новое состояние реле."""
    url = f"{SERVER_URL}/api/relay/check"
    payload = {
        "modul_id": MODUL_ID,
        "relay_pin": relay_pin,
        "state": current_state
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            new_state = data.get("state", current_state)
            mode      = data.get("mode", "?")
            alarm     = data.get("alarm", False)

            state_str = "ВКЛ" if new_state else "ВЫКЛ"
            alarm_str = " ⚠️ АВАРИЯ (расхождение состояний!)" if alarm else ""
            print(f"  [{relay_pin}] mode={mode} state={state_str}{alarm_str}")

            return new_state
        else:
            print(f"  [{relay_pin}] Ошибка сервера: {resp.status_code}")
            return current_state
    except Exception as e:
        print(f"  [{relay_pin}] Ошибка соединения: {e}")
        return current_state


def run():
    print(f"Запуск эмулятора реле (modul_id={MODUL_ID})...")
    print(f"Реле: {[r['relay_pin'] for r in RELAYS]}")
    print(f"Интервал опроса: {SEND_INTERVAL} сек\n")

    while True:
        print(f"--- Опрос сервера ---")
        for relay in RELAYS:
            new_state = check_relay(relay["relay_pin"], relay["state"])
            relay["state"] = new_state  # обновляем локальное состояние

        time.sleep(SEND_INTERVAL)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nЭмуляция остановлена.")
