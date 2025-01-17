from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def init_ai_assistant():
    with app.app_context():
        # 检查AI助手是否已存在
        bot = User.query.filter_by(username='AI助手').first()
        if not bot:
            # 创建AI助手用户
            bot = User(
                username='AI助手',
                email='ai@assistant.com',
                password_hash=generate_password_hash('ai_assistant_password'),
                is_bot=True
            )
            db.session.add(bot)
            db.session.commit()
            print("AI助手已创建")
        else:
            print("AI助手已存在")
