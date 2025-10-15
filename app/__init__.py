"""
[Flask应用工厂模式]
创建和配置Flask应用实例
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import config
'''
# 1. 启动应用时
python run.py

# 2. run.py 中的代码
from app import create_app  # 这里会触发 app/__init__.py 的执行

# 3. 当执行 from app import create_app 时，Python会：
#    - 加载 app/__init__.py 文件
#    - 执行文件中的代码，包括：
#      - import os
#      - from flask import Flask  
#      - from flask_sqlalchemy import SQLAlchemy
#      - db = SQLAlchemy()  # ← 这里被执行！
#      - login_manager = LoginManager()
#      - def create_app(): ...
'''
# [全局变量初始化]
# db = SQLAlchemy() 这行代码的执行时机不是在所有代码之前，而是在app模块被第一次导入时。
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()

def create_app(config_name=None):
    """
    [应用工厂函数]
    根据配置创建Flask应用实例
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # [创建Flask应用]
    app = Flask(__name__)
    
    # [加载配置]
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # [初始化扩展]
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # [配置登录管理器]
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """[用户加载回调函数]"""
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # [注册蓝图]
    from app.views.auth import auth
    from app.views.user import user
    from app.views.admin import admin
    
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(user)
    app.register_blueprint(admin)
    
    # [自定义Jinja2过滤器]
    @app.template_filter('from_json')
    def from_json_filter(value):
        """JSON字符串转Python对象"""
        import json
        try:
            return json.loads(value) if value else []
        except:
            return []
    
    # [主页路由]
    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('user.dashboard'))
        else:
            return redirect(url_for('auth.login'))
    
    # [初始化任务调度器]
    from app.scheduler import task_scheduler
    task_scheduler.init_app(app)
    
    # [创建数据库表]
    with app.app_context():
        # 导入所有模型以确保它们被注册
        from app.models import User, File, Task, TaskExecution
        from app.models.url_context import UrlUpdateContext, UrlMenu, BatchUrlFind
        
        db.create_all()
        
        # [创建默认管理员账户]
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            admin_user.is_admin = True
            db.session.add(admin_user)
            db.session.commit()
            app.logger.info('默认管理员账户已创建: admin/admin123')
    
    return app, socketio