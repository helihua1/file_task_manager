"""
[1-4] 任务执行记录数据模型
记录每次任务执行的详细信息和结果
"""
from datetime import datetime
from app import db
from app.models.url_context import UrlUpdateContext


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
    status = db.Column(db.String(100), comment='执行状态')
    error_message = db.Column(db.Text, comment='信息')
    response_data = db.Column(db.Text, comment='响应数据')
    
    # [1-4.1.3] 执行URL相关字段
    execute_url = db.Column(db.String(500), comment='执行的目标URL')
    url_menu_value = db.Column(db.String(100), comment='URL栏目值')
    url_menu_text = db.Column(db.String(200), comment='URL栏目文本')
    
    def __init__(self, task_id, file_id, status, error_message=None, response_data=None, 
                 execute_url=None, url_menu_value=None, url_menu_text=None):
        """
        [1-4.1.4] 执行记录对象初始化
        """
        self.task_id = task_id
        self.file_id = file_id
        self.status = status
        self.error_message = error_message
        self.response_data = response_data
        self.execute_url = execute_url
        self.url_menu_value = url_menu_value
        self.url_menu_text = url_menu_text

    @classmethod
    def get_url_execution_stats(cls, task_id, url_configs):
        """
        [5-1.4] 获取按URL和菜单值分组的执行统计

        参数:
            task_id: 任务ID
            url_configs: URL配置列表，格式 [{'url': 'http://xxx', 'menu_value': '4'}, ...]

        返回:
            统计数据列表，每个URL一条记录
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func

        # 计算今天和昨天的日期范围
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        today_start = datetime.combine(today, datetime.min.time())
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        yesterday_end = datetime.combine(yesterday, datetime.max.time())

        stats = []

        for config in url_configs:
            url = config.get('url', '')
            menu_value = config.get('menu_value', '')
            menu_text = config.get('menu_text', '')

            # 查询该URL和menu_value的所有执行记录
            base_query = cls.query.filter_by(
                task_id=task_id,
                execute_url=url,
                url_menu_value=menu_value
            )

            # 总执行数量
            total_count = base_query.count()

            # 昨天执行数量
            yesterday_count = base_query.filter(
                cls.execution_time >= yesterday_start,
                cls.execution_time <= yesterday_end
            ).count()

            # 今天执行数量
            today_count = base_query.filter(
                cls.execution_time >= today_start
            ).count()

            menu_text = UrlUpdateContext.get_menu_text_by_root_url_and_menu_value(url, menu_value)

            stats.append({
                'url': url,
                'menu_value': menu_value,
                'menu_text': menu_text,
                'total_count': total_count,
                'yesterday_count': yesterday_count,
                'today_count': today_count
            })

        return stats






    # =========下面为管理员方法==========

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
            'response_data': self.response_data,
            'execute_url': self.execute_url,
            'url_menu_value': self.url_menu_value,
            'url_menu_text': self.url_menu_text
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