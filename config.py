import os

# Определяем путь к папке, где лежит этот файл
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 1. Путь к файлу SQLite (создастся в корне проекта)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'sensors.db')
    
    # 2. Настройки соединения (Важно!)
    # connect_args помогает избежать ошибок блокировки базы при записи/чтении
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"timeout": 15}
    }

    # 3. Отладка (Включи True, если хочешь видеть SQL-запросы в консоли)
    SQLALCHEMY_ECHO = False 
    
    # 4. Ресурсы. Отключаем лишнюю функцию слежения (экономит ресурсы)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 5. Безопасность. Секретный ключ для сессий и защиты (аналог cookieValidationKey в Yii2)
    # В идеале брать из переменной окружения, но для локального сервера пойдет так
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-super-secret-key-123'

    # 6. Настройки приложения (можно добавить свои)
    DEBUG = True