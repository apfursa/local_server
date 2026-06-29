import socket
import threading
import logging
import socket


def get_local_ip():
    # Трюк, чтобы узнать свой IP в локальной сети
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def _udp_discovery_worker():
    server_ip = get_local_ip()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Слушаем все входящие UDP-пакеты на порту 8888
    sock.bind(("", 8888))

    logging.info(f"[UDP] Слушатель запущен на {server_ip}:8888")

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            if data.decode() == "DISCOVER_SERVER":
                response = f"SERVER_IP:{server_ip}"
                sock.sendto(response.encode(), addr)
                logging.info(f"[UDP] Ответил датчику {addr[0]} на запрос IP")
        except Exception as e:
            logging.error(f"[UDP] Ошибка в потоке: {e}")


def start_udp():
    thread = threading.Thread(target=_udp_discovery_worker, daemon=True)
    thread.start()
    logging.info("[UDP] Фоновый поток обнаружения инициализирован.")