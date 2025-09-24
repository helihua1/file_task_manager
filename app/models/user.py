"""
[1-1] 用户数据模型
负责用户认证和基本信息管理
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    [1-1.1] 用户模型类
    继承UserMixin以支持Flask-Login认证功能
    """
    __tablename__ = 'users'
    
    # [1-1.1.1] 用户基本信息字段定义
    id = db.Column(db.Integer, primary_key=True, comment='用户ID主键')
    username = db.Column(db.String(80), unique=True, nullable=False, comment='用户名，唯一标识')
    email = db.Column(db.String(120), unique=True, nullable=False, comment='邮箱地址，唯一标识')
    password_hash = db.Column(db.String(128), nullable=False, comment='密码哈希值')
    is_admin = db.Column(db.Boolean, default=False, comment='是否为管理员')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='用户创建时间')
    last_login = db.Column(db.DateTime, comment='最后登录时间')
    
    # [1-1.1.2] 关联关系定义
    files = db.relationship('File', backref='user', lazy='dynamic', cascade='all, delete-orphan', 
                           comment='用户上传的文件列表')
    tasks = db.relationship('Task', backref='user', lazy='dynamic', cascade='all, delete-orphan',
                           comment='用户创建的任务列表')
    
    def __init__(self, username, email, password):
        """
        [1-1.1.3] 用户对象初始化
        自动生成密码哈希值
        """
        self.username = username
        self.email = email
        self.set_password(password)
    
    def set_password(self, password):
        """
        [1-1.2] 设置用户密码
        使用Werkzeug生成安全的密码哈希
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        [1-1.3] 验证用户密码
        与存储的哈希值进行比对
        """
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """
        [1-1.4] 更新最后登录时间
        用户成功登录后调用
        """
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def get_upload_stats(self):
        """
        [1-1.5] 获取用户文件上传统计信息
        返回总文件数和已执行文件数
        """
        total_files = self.files.count()
        executed_files = self.files.filter_by(is_executed=True).count()
        return {
            'total_files': total_files,
            'executed_files': executed_files,
            'pending_files': total_files - executed_files
        }
    
    def get_task_stats(self):
        """
        [1-1.6] 获取用户任务统计信息
        返回各状态任务的数量
        """
        tasks = self.tasks.all()
        stats = {
            'total_tasks': len(tasks),
            'running_tasks': len([t for t in tasks if t.status == 'running']),
            'completed_tasks': len([t for t in tasks if t.status == 'completed']),
            'failed_tasks': len([t for t in tasks if t.status == 'failed'])
        }
        return stats
    
    def __repr__(self):
        """
        [1-1.7] 用户对象字符串表示
        """
        return f'<User {self.username}>'