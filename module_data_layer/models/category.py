from module_data_layer.core.db_config import db

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'location' или 'group'

    def to_dict(self):
        return {"id": self.id, "name": self.name, "type": self.type}