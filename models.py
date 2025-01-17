from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_bot = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    messages_sent = db.relationship('Message',
                                  foreign_keys='Message.sender_id',
                                  backref='sender', lazy=True,
                                  cascade='all, delete-orphan')
    messages_received = db.relationship('Message',
                                      foreign_keys='Message.recipient_id',
                                      backref='recipient', lazy=True)
    files = db.relationship('FileShare', backref='owner', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)

    def __repr__(self):
        return f'<Post {self.title}>'

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)  # 文本内容
    message_type = db.Column(db.String(20), nullable=False)  # text, image, voice
    media_url = db.Column(db.String(500))  # 媒体文件URL
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    status = db.Column(db.String(20), default='sending')  # sending, sent, read
    read_at = db.Column(db.DateTime)  # 消息已读时间

    def __repr__(self):
        return f'<Message {self.content[:20]}...>'

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'message_type': self.message_type,
            'media_url': self.media_url,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'status': self.status,
            'read_at': self.read_at.strftime('%Y-%m-%d %H:%M:%S') if self.read_at else None
        }

class FileShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False, index=True)
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    file_type = db.Column(db.String(50), index=True)  # 文件类型，如 docx, pdf 等
    upload_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    description = db.Column(db.String(500))  # 文件描述

    def __repr__(self):
        return f'<FileShare {self.original_filename}>'

def init_ai_assistant(app):
    """初始化AI助手用户"""
    with app.app_context():
        try:
            ai_assistant = User.query.filter_by(username='AI助手').first()
            if not ai_assistant:
                ai_assistant = User(
                    username='AI助手',
                    email='ai@assistant.com',
                    password=generate_password_hash('ai_assistant_password'),
                    is_bot=True
                )
                db.session.add(ai_assistant)
                db.session.commit()
                print("AI助手用户创建成功")
            return ai_assistant
        except Exception as e:
            db.session.rollback()
            print(f"初始化AI助手失败: {str(e)}")
            return None
