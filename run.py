import os  # Модуль для работы с операционной системой (проверка файлов, путей)
from flask import Flask  # Основной класс для создания веб-приложения
from config import Config  # Твой класс с настройками (путь к БД, секретные ключи)
from core.db_config import db, migrate  # Объекты базы данных и системы миграций

def create_app():
    """Фабрика приложения (аналог точки входа в Yii2)"""
    # Создаем объект Flask. 
    # __name__ помогает Flask найти корень проекта.
    # template_folder и static_folder указывают, где лежат HTML и JS/CSS.
    app = Flask(__name__, 
                template_folder='web/templates', 
                static_folder='web/static')
    
    # 1. Загружаем конфигурацию (пути к БД, ключи)
    # Переносим все настройки из класса Config в системный словарь app.config
    app.config.from_object(Config)

    # 2. Инициализируем SQLAlchemy и Flask-Migrate.
    # Связываем объекты БД с конкретным созданным приложением app
    db.init_app(app)
    migrate.init_app(app, db)

    # 3. Регистрируем контроллеры (Blueprints)
    # Импортируем их внутри функции, чтобы избежать проблем с цикличными импортами
    # (когда контроллер просит app, а app просит контроллер — всё зависает)
    from controllers.views_controller import views_bp
    from controllers.api_controller import api_bp
    from controllers.settings_controller import settings_bp
    from controllers.sync_controller import sync_bp

    # Подключаем модули (чертежи) к приложению, чтобы Flask знал, какие URL обрабатывать
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(sync_bp)

    # 4. Проверяем наличие всех моделей для корректной работы миграций
    # Входим в "контекст приложения", чтобы Flask "увидел" базу данных
    with app.app_context():
        # Импортируем модели, чтобы SQLAlchemy "узнала" о существовании таблиц
        from models.device import Device
        from models.measurement import Measurement
        from models.setting import Setting
        
        # Если ты не хочешь использовать миграции, а просто создать таблицы "как есть":
        # db.create_all() 
        # Но мы используем миграции (flask db upgrade), так что это закомментировано.

    return app  # Возвращаем полностью настроенное приложение

# Создаем экземпляр приложения, вызывая функцию-фабрику
app = create_app()

def setup_database(app):
    # Опять входим в контекст, так как работаем с настройками и БД
    with app.app_context():
        # Извлекаем путь к файлу БД из конфига, убирая префикс sqlite:///
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI').replace('sqlite:///', '')
        
        # Если файла базы нет на диске ИЛИ его размер 0 байт (пустой файл)
        if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
            print("--- ВНИМАНИЕ: База данных не обнаружена или пуста. Создаю таблицы... ---")
            # Автоматически создаем все таблицы на основе импортированных моделей
            db.create_all() 
            print("--- База данных успешно инициализирована! ---")
        else:
            # Если файл есть, просто подтверждаем готовность
            print("--- База данных обнаружена, таблицы готовы. ---")

# Вызываем проверку перед запуском сервера, чтобы база точно была готова
setup_database(app)

# Проверка: запущен ли файл напрямую (а не импортирован как модуль)
if __name__ == '__main__':
    # 1. Импортируем функции запуска фоновых процессов
    from background.mqtt import start_mqtt
    from background.sync import start_sync
    
    # 2. Запускаем MQTT в фоновом потоке (через loop_start внутри функции)
    # Он будет слушать ESP8266, пока работает сайт
    start_mqtt() 
    
    # 3. Запускаем Синхронизацию в фоновом потоке (передаем app для доступа к БД)
    # Она будет раз в минуту общаться с твоим сервером api.apinjener.ru
    start_sync(app)
    
    print("Фоновые процессы (MQTT и Синхронизация) запущены.")
    print("Сервер стартует на http://localhost:80")
    
    # 4. Запускаем сам веб-сервер Flask
    # host='0.0.0.0' делает сервер доступным во всей локальной сети (не только localhost)
    # port=80 — стандартный порт для браузера
    # debug=True — сервер будет сам перезагружаться при изменении кода
    # use_reloader=False — КРИТИЧНО: без этого Flask запустит два процесса, 
    # и у тебя будет два MQTT-клиента и две синхронизации, что приведет к ошибкам в БД.
    app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)