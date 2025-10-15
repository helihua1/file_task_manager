"""
[1-3] 任务数据模型
管理用户创建的定时任务信息和执行状态
"""
from datetime import datetime
from app import db

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
    target_url = db.Column(db.String(15000), nullable=False, comment='目标网站URL')
    execution_method = db.Column(db.String(100), nullable=False, comment='执行方法名称')
    
    # [1-3.1.2] 任务调度配置字段
    interval_seconds = db.Column(db.Integer, nullable=False, comment='执行间隔(秒)')
    start_time = db.Column(db.DateTime, nullable=False, comment='任务开始时间')
    end_time = db.Column(db.DateTime, comment='任务结束时间')
    
    # [1-3.1.3] 新增字段 - 任务配置
    source_folder = db.Column(db.String(200), nullable=True, comment='源文件夹名称')
    backup_folders = db.Column(db.Text, nullable=True, comment='备用文件夹列表(JSON格式)')
    daily_start_time = db.Column(db.Time, nullable=True, comment='每日开始执行时间')
    daily_execution_count = db.Column(db.Integer, default=1, comment='每个网站每日执行数量')
    
    # [1-3.1.4] 任务状态字段
    status = db.Column(db.Enum('pending', 'running', 'paused', 'completed', 'failed', name='task_status'),
                      default='pending', comment='任务状态')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='任务创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='任务更新时间')
    
    # [1-3.1.5] 任务统计字段
    # executed_files_count = db.Column(db.Integer, default=0, comment='已执行文件数量')
    # total_files_count = db.Column(db.Integer, default=0, comment='总文件数量')
    
    # [1-3.1.6] 关联关系
    task_executions = db.relationship('TaskExecution', backref='task', lazy='dynamic',
                                    cascade='all, delete-orphan')
    
    def __init__(self, user_id, task_name, target_url, execution_method, 
                 interval_seconds, start_time, end_time=None, source_folder=None,
                 backup_folders=None, daily_start_time=None, daily_execution_count=1):
        """
        [1-3.1.7] 任务对象初始化
        """
        self.user_id = user_id
        self.task_name = task_name
        self.target_url = target_url
        self.execution_method = execution_method
        self.interval_seconds = interval_seconds
        self.start_time = start_time
        self.end_time = end_time
        self.source_folder = source_folder
        self.backup_folders = backup_folders
        self.daily_start_time = daily_start_time
        self.daily_execution_count = daily_execution_count
        # self.update_file_count()
    
    # def update_file_count(self):
    #     """
    #     [3-1.4] 更新任务关联的文件数量
    #     创建任务时计算用户未执行的文件总数（包含主文件夹和备用文件夹）
    #     """
    #     from .file import File
    #     import os
    #     import json
        
    #     query = File.query.filter_by(
    #         user_id=self.user_id, 
    #         is_executed=False
    #     )
        
    #     # 如果指定了源文件夹，计算该文件夹及备用文件夹的文件
    #     if self.source_folder:
    #         folders = [self.source_folder]
            
    #         # 添加备用文件夹
    #         if self.backup_folders:
    #             try:
    #                 backup_list = json.loads(self.backup_folders)
    #                 folders.extend(backup_list)
    #             except:
    #                 pass
            
    #         # 构建多个文件夹的OR条件
    #         folder_conditions = []
    #         for folder in folders:
    #             folder_conditions.append(File.file_path.like(f'%{os.sep}{folder}{os.sep}%'))
    #             folder_conditions.append(File.file_path.like(f'%\\{folder}\\%'))
            
    #         if folder_conditions:
    #             query = query.filter(db.or_(*folder_conditions))
        
    #     self.total_files_count = query.count()
    #     db.session.commit()
    
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
        import os
        
        # 构建原生SQL查询
        if self.source_folder:
            # 如果指定了源文件夹，使用原生SQL查询
            sql = """
            SELECT * FROM files 
            WHERE user_id = :user_id 
            AND is_executed = 0 
            AND (file_path LIKE :linux_pattern OR file_path LIKE :windows_pattern)
            ORDER BY id ASC 
            LIMIT 1
            """
            
            # 构建路径模式
            linux_pattern = f'%{os.sep}{self.source_folder}{os.sep}%'
            windows_pattern = f'%\\\\{self.source_folder}\\\\%'
            
            # 执行原生SQL查询
            result = db.session.execute(
                db.text(sql), 
                {
                    'user_id': self.user_id,
                    'linux_pattern': linux_pattern,
                    'windows_pattern': windows_pattern
                }
            ).fetchone()
            
            # 将结果转换为File对象
            if result:
                return File.query.get(result.id)
            return None
    
    # def increment_executed_count(self):
    #     """
    #     [4-2.5] 增加已执行文件计数
    #     每次文件执行完成后调用
    #     """
    #     self.executed_files_count += 1
    #     self.updated_at = datetime.utcnow()
        
    #     # 检查是否所有文件都已执行完成
    #     if self.executed_files_count >= self.total_files_count:
    #         self.complete_task()
    #     else:
    #         db.session.commit()
    
    # def get_progress_percentage(self):
    #     """
    #     [4-1.5] 获取任务执行进度百分比
    #     用于前端显示进度条
    #     """
    #     if self.total_files_count == 0:
    #         return 0
    #     return round((self.executed_files_count / self.total_files_count) * 100, 2)
    
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
            'source_folder': self.source_folder,
            'daily_start_time': self.daily_start_time.strftime('%H:%M') if self.daily_start_time else None,
            'daily_execution_count': self.daily_execution_count,
            'status': self.status,
            # 'progress': self.get_progress_percentage(),
            # 'executed_files': self.executed_files_count,
            # 'total_files': self.total_files_count,
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
        
        return True
    
    def __repr__(self):
        """
        [1-3.3] 任务对象字符串表示
        """
        return f'<Task {self.task_name} (User: {self.user_id}, Status: {self.status})>'