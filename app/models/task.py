"""
[1-3] 任务数据模型
管理用户创建的定时任务信息和执行状态
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Task(db.Model):
    """
    [1-3.1] 任务模型类
    存储定时任务的配置信息和执行状态
    """
    __tablename__ = 'tasks'
    
    # [1-3.1.1] 任务基本信息字段
    id = db.Column(db.Integer, primary_key=True, comment='任务ID主键')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='所属用户ID')
    task_name = db.Column(db.String(200), nullable=False, comment='任务名称')
    target_url = db.Column(db.String(500), nullable=False, comment='目标网站URL')
    execution_method = db.Column(db.String(100), nullable=False, comment='执行方法名称')
    
    # [1-3.1.2] 任务调度配置字段
    interval_seconds = db.Column(db.Integer, nullable=False, comment='执行间隔(秒)')
    start_time = db.Column(db.DateTime, nullable=False, comment='任务开始时间')
    end_time = db.Column(db.DateTime, comment='任务结束时间')
    
    # [1-3.1.3] 任务状态字段
    status = db.Column(db.Enum('pending', 'running', 'paused', 'completed', 'failed', name='task_status'),
                      default='pending', comment='任务状态')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='任务创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='任务更新时间')
    
    # [1-3.1.4] 任务统计字段
    executed_files_count = db.Column(db.Integer, default=0, comment='已执行文件数量')
    total_files_count = db.Column(db.Integer, default=0, comment='总文件数量')
    
    # [1-3.1.5] 关联关系
    task_executions = db.relationship('TaskExecution', backref='task', lazy='dynamic',
                                    cascade='all, delete-orphan'
                                      )
                                      # , comment='任务执行记录')
    
    def __init__(self, user_id, task_name, target_url, execution_method, 
                 interval_seconds, start_time, end_time=None):
        """
        [1-3.1.6] 任务对象初始化
        """
        self.user_id = user_id
        self.task_name = task_name
        self.target_url = target_url
        self.execution_method = execution_method
        self.interval_seconds = interval_seconds
        self.start_time = start_time
        self.end_time = end_time
        self.update_file_count()
    
    def update_file_count(self):
        """
        [3-1.4] 更新任务关联的文件数量
        创建任务时计算用户未执行的文件总数
        """
        from .file import File
        self.total_files_count = File.query.filter_by(
            user_id=self.user_id, 
            is_executed=False
        ).count()
        db.session.commit()
    
    def start_task(self):
        """
        [4-1.1] 启动任务
        将任务状态设置为运行中
        """
        self.status = 'running'
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def pause_task(self):
        """
        [4-1.2] 暂停任务
        将任务状态设置为暂停
        """
        self.status = 'paused'
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def complete_task(self):
        """
        [4-1.3] 完成任务
        所有文件执行完毕后调用
        """
        self.status = 'completed'
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def fail_task(self, error_message=None):
        """
        [4-1.4] 任务执行失败
        遇到严重错误时调用
        """
        self.status = 'failed'
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def get_next_file(self):
        """
        [4-2.1] 获取下一个待执行的文件
        返回用户的第一个未执行文件
        """
        from .file import File
        return File.query.filter_by(
            user_id=self.user_id,
            is_executed=False
        ).first()
    
    def increment_executed_count(self):
        """
        [4-2.5] 增加已执行文件计数
        每次文件执行完成后调用
        """
        self.executed_files_count += 1
        self.updated_at = datetime.utcnow()
        
        # 检查是否所有文件都已执行完成
        if self.executed_files_count >= self.total_files_count:
            self.complete_task()
        else:
            db.session.commit()
    
    def get_progress_percentage(self):
        """
        [4-1.5] 获取任务执行进度百分比
        用于前端显示进度条
        """
        if self.total_files_count == 0:
            return 0
        return round((self.executed_files_count / self.total_files_count) * 100, 2)
    
    def get_task_info(self):
        """
        [1-3.2] 获取任务详细信息
        返回包含任务状态的字典
        """
        return {
            'id': self.id,
            'task_name': self.task_name,
            'target_url': self.target_url,
            'execution_method': self.execution_method,
            'interval_seconds': self.interval_seconds,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'status': self.status,
            'progress': self.get_progress_percentage(),
            'executed_files': self.executed_files_count,
            'total_files': self.total_files_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def can_execute(self):
        """
        [4-1.6] 检查任务是否可以执行
        判断任务状态和时间条件
        """
        now = datetime.utcnow()
        
        # 检查任务状态
        if self.status not in ['running']:
            return False
        
        # 检查开始时间
        if now < self.start_time:
            return False
        
        # 检查结束时间
        if self.end_time and now > self.end_time:
            self.complete_task()
            return False
        
        return True
    
    def __repr__(self):
        """
        [1-3.3] 任务对象字符串表示
        """
        return f'<Task {self.task_name} (User: {self.user_id}, Status: {self.status})>'