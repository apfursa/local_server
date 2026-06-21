from module_data_layer.core.db_config import db


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255), nullable=False)
    data_type = db.Column(db.String(20), default='string')  # string, integer, boolean
    name = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(255), nullable=True)

    @classmethod
    def get_val(cls, key_name, default=None):
        """Удобный метод: сразу достает настройку и конвертирует в нужный тип"""
        setting = db.session.query(cls).filter_by(key=key_name).first()
        if not setting:
            return default

        if setting.data_type == 'integer':
            return int(setting.value)
        if setting.data_type == 'boolean':
            return setting.value.lower() in ['1', 'true', 'yes']
        return setting.value