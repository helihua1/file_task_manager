"""
URL上下文数据模型
用于管理URL更新上下文和菜单数据
"""
from datetime import datetime
from urllib.parse import urljoin
import requests
from app import db


class UrlUpdateContext(db.Model):
    """
    URL更新上下文模型
    存储网站的基本连接信息
    """
    __tablename__ = 'url_update_contexts'
    
    id = db.Column(db.Integer, primary_key=True, comment='主键ID')
    name = db.Column(db.String(100), nullable=True, comment='URL名称')
    root_url = db.Column(db.String(255), nullable=False, comment='根域名')
    suffix = db.Column(db.String(255), nullable=False, comment='后缀路径')
    username = db.Column(db.String(80), nullable=False, comment='用户名')
    password = db.Column(db.String(128), nullable=False, comment='密码')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    
    # 关联关系
    menus = db.relationship('UrlMenu', backref='context', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def base_url(self):
        """获取完整的基础URL"""
        return urljoin(self.root_url, self.suffix)
    
    def create_session_context(self):
        """创建用于请求的会话上下文"""
        session = requests.Session()
        return {
            'session': session,
            'root_url': self.root_url,
            'suffix': self.suffix,
            'username': self.username,
            'password': self.password,
            'base_url': self.base_url
        }
    
    def __repr__(self):
        return f'<UrlUpdateContext {self.root_url}{self.suffix}>'


class UrlMenu(db.Model):
    """
    URL菜单模型
    存储从网站获取的菜单信息
    """
    __tablename__ = 'url_menus'
    
    id = db.Column(db.Integer, primary_key=True, comment='主键ID')
    context_id = db.Column(db.Integer, db.ForeignKey('url_update_contexts.id'), nullable=False, comment='关联的上下文ID')
    menu_value = db.Column(db.String(50), nullable=False, comment='菜单值')
    menu_text = db.Column(db.String(200), nullable=False, comment='菜单文本')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    
    def __repr__(self):
        return f'<UrlMenu {self.menu_value}: {self.menu_text}>'


# 为了兼容testtest.py中的类，创建一个简单的类
class url_update_context:
    """
    简单的URL更新上下文类，用于与test.py兼容
    """
    def __init__(self, session, root_url, suffix, username, password):
        self.session = session
        self.suffix = suffix
        self.root_url = root_url
        self.base_url = urljoin(self.root_url, self.suffix)
        self.username = username
        self.password = password
