"""
Модуль инициализации ядра СУБД.
Создает объекты Flask-SQLAlchemy и Flask-Migrate для управления СУБД SQLite.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Глобальные инстансы ORM и миграций
db = SQLAlchemy()
migrate = Migrate()
