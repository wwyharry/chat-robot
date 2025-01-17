from app import app, db
from models import FileShare

def migrate():
    with app.app_context():
        # 创建 file_share 表
        db.create_all()
        print("FileShare table created successfully!")

if __name__ == '__main__':
    migrate()
