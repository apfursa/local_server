"""module_ingestion — приёмник данных (Ingestion Layer).

Фоновый процесс: держит подключение к локальному MQTT-брокеру Mosquitto,
перехватывает пакеты от модулей ESP8266, валидирует их и передаёт в слой
хранения (module_data_layer) через методы Device/Measurement (ТЗ №2).
"""
