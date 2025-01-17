from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_socketio import SocketIO
from models import db, User, Message, Post, FileShare
from events import init_socket_events
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 文件上传配置
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'images'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'voices'), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 初始化数据库
db.init_app(app)

# 初始化SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# 确保数据库表存在
with app.app_context():
    db.create_all()

# 初始化Socket.IO事件
init_socket_events(app, socketio)

# 错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

@app.errorhandler(413)
def request_entity_too_large(e):
    flash('文件太大，请上传小于50MB的文件', 'error')
    return redirect(request.url)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('chat'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            if remember:
                # 设置session的持久化
                session.permanent = True
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([username, email, password, confirm_password]):
            flash('请填写所有字段', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册', 'error')
            return render_template('register.html')

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('注册成功，请登录', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('注册失败，请稍后重试', 'error')
            app.logger.error(f'用户注册失败: {str(e)}')

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('您已成功退出登录', 'success')
    return redirect(url_for('login'))

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 获取AI助手用户
    ai_assistant = User.query.filter_by(username='AI助手').first()
    if not ai_assistant:
        flash('系统错误：AI助手未配置', 'error')
        return redirect(url_for('index'))
    
    return render_template('chat.html', bot=ai_assistant)

@app.route('/files')
def files():
    if 'user_id' not in session:
        flash('请先登录', 'error')
        return redirect(url_for('login'))
    
    files = FileShare.query.order_by(FileShare.upload_time.desc()).all()
    return render_template('files.html', files=files)

@app.route('/create-post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        flash('请先登录', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('标题和内容不能为空', 'error')
            return render_template('create_post.html')
        
        post = Post(
            title=title,
            content=content,
            user_id=session['user_id']
        )
        
        try:
            db.session.add(post)
            db.session.commit()
            flash('帖子发布成功！', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('发布失败，请稍后重试', 'error')
            app.logger.error(f'发布帖子失败: {str(e)}')
    
    return render_template('create_post.html')

@app.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('view_post.html', post=post)

if __name__ == '__main__':
    socketio.run(app, debug=True)