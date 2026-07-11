import os
from flask import Flask
from config import Config

# База данных и миграции из слоя данных
from module_data_layer.core.db_config import db, migrate


def create_app():
    """Фабрика приложения, собранная по твоей реальной модульной структуре"""
    app = Flask(__name__,
                template_folder='module_presentation/web/templates',
                static_folder='module_presentation/web/static')

    app.config.from_object(Config)

    # Инициализация БД
    db.init_app(app)
    migrate.init_app(app, db)

    # ИМПОРТ КОНТРОЛЛЕРОВ
    from module_presentation.controllers.views_controller import views_bp
    from module_business_logic.controllers.api_controller import api_bp
    from module_business_logic.controllers.settings_controller import settings_bp
    from module_business_logic.controllers.alarm_controller import alarm_bp
    from module_sync.controllers.sync_controller import sync_bp
    from module_business_logic.controllers.category_controller import category_bp
    from module_business_logic.controllers.phone_controller import phone_bp
    from module_business_logic.controllers.sort_controller import sort_bp
    from module_business_logic.controllers.ota_controller import ota_bp
    from module_business_logic.controllers.relay_controller import relay_bp
    from module_ingestion.controllers.ingestion_controller import ingestion_bp

    # Регистрация блупринтов
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(sync_bp, url_prefix='/sync')
    app.register_blueprint(alarm_bp, url_prefix='/api/alarm')
    app.register_blueprint(category_bp, url_prefix='/api/categories')
    app.register_blueprint(phone_bp, url_prefix='/phone')
    app.register_blueprint(sort_bp, url_prefix='/sort')
    app.register_blueprint(ota_bp, url_prefix='/api/ota')
    app.register_blueprint(relay_bp, url_prefix='/api/relay')
    app.register_blueprint(ingestion_bp, url_prefix='/ingest')

    # Подгружаем модели для работы миграций
    with app.app_context():
        import module_data_layer.models

    return app


app = create_app()


def setup_database(app):
    """Автоматическое создание таблиц при чистом старте"""
    with app.app_context():
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI').replace('sqlite:///', '')
        if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
            print("--- ВНИМАНИЕ: База данных не обнаружена. Создаю таблицы... ---")
            db.create_all()
            print("--- База данных успешно инициализирована! ---")
        else:
            print("--- База данных обнаружена, таблицы готовы. ---")


setup_database(app)

if __name__ == '__main__':
    from module_ingestion.background.mqtt import start_mqtt
    from module_sync.background.sync import start_sync
    from module_network.discovery import start_udp

    start_mqtt(app)
    start_sync()
    start_udp()

    print("Фоновые процессы запущены.")
    print("Сервер стартует на http://localhost:80")

    app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)
