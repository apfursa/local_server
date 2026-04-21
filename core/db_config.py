from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Создаем пустые объекты. Мы "привяжем" их к приложению чуть позже в run.py
db = SQLAlchemy()
migrate = Migrate()