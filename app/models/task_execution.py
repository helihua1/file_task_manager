"""
[1-4] 任务执行记录数据模型
记录每次任务执行的详细信息和结果
"""
from datetime import datetime
from app import db

class TaskExecution(db.Model):
    """
    [1-4.1] 任务执行记录模型类
    记录每次文件执行的详细信息
    """
    __tablename__ = 'task_executions'
    
    # [1-4.1.1] 执行记录基本字段
    id = db.Column(db.Integer, primary_key=True, comment='执行记录ID主键')
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, comment='所属任务ID')
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False, comment='执行的文件ID')
    execution_time = db.Column(db.DateTime, default=datetime.utcnow, comment='执行时间')
    
    # [1-4.1.2] 执行结果字段
    status = db.Column(db.Enum('success', 'failed', name='execution_status'), 
                      nullable=False, comment='执行状态')
    error_message = db.Column(db.Text, comment='错误信息')
    response_data = db.Column(db.Text, comment='响应数据')
    
    def __init__(self, task_id, file_id, status, error_message=None, response_data=None):
        """
        [1-4.1.3] 执行记录对象初始化
        """
        self.task_id = task_id
        self.file_id = file_id
        self.status = status
        self.error_message = error_message
        self.response_data = response_data
    
    @classmethod
    def create_success_record(cls, task_id, file_id, response_data=None):
        """
        [4-2.6] 创建成功执行记录
        文件执行成功后调用
        """
        record = cls(
            task_id=task_id,
            file_id=file_id,
            status='success',
            response_data=response_data
        )
        db.session.add(record)
        db.session.commit()
        return record
    
    @classmethod
    def create_failed_record(cls, task_id, file_id, error_message):
        """
        [4-2.7] 创建失败执行记录
        文件执行失败后调用
        """
        record = cls(
            task_id=task_id,
            file_id=file_id,
            status='failed',
            error_message=error_message
        )
        db.session.add(record)
        db.session.commit()
        return record
    
    def get_execution_info(self):
        """
        [1-4.2] 获取执行记录详细信息
        返回包含执行结果的字典
        """
        return {
            'id': self.id,
            'task_id': self.task_id,
            'file_id': self.file_id,
            'execution_time': self.execution_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status,
            'error_message': self.error_message,
            'response_data': self.response_data
        }
    
    @classmethod
    def get_task_execution_history(cls, task_id, limit=50):
        """
        [5-1.2] 获取任务执行历史记录
        管理员监控和用户查看历史时使用
        """
        records = cls.query.filter_by(task_id=task_id)\
                          .order_by(cls.execution_time.desc())\
                          .limit(limit).all()
        return [record.get_execution_info() for record in records]
    
    @classmethod
    def get_user_execution_stats(cls, user_id):
        """
        [5-1.3] 获取用户执行统计信息
        管理员监控时使用
        """
        from .task import Task
        
        # 查询用户的所有任务执行记录
        records = db.session.query(cls)\
                           .join(Task, cls.task_id == Task.id)\
                           .filter(Task.user_id == user_id).all()
        
        total_executions = len(records)
        success_executions = len([r for r in records if r.status == 'success'])
        failed_executions = total_executions - success_executions
        
        return {
            'total_executions': total_executions,
            'success_executions': success_executions,
            'failed_executions': failed_executions,
            'success_rate': round((success_executions / total_executions * 100), 2) if total_executions > 0 else 0
        }
    
    def __repr__(self):
        """
        [1-4.3] 执行记录对象字符串表示
        """
        return f'<TaskExecution Task:{self.task_id} File:{self.file_id} Status:{self.status}>'