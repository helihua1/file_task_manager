"""
[任务调度系统]
使用APScheduler实现定时任务的调度和执行
"""
import requests
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.models.task import Task
from app.models.file import File
from app.models.task_execution import TaskExecution
from app.models import db

# [4] 任务调度器初始化
scheduler = BackgroundScheduler()
logger = logging.getLogger(__name__)

class TaskScheduler:
    """
    [4-1] 任务调度管理器
    负责管理所有定时任务的调度和执行
    """
    
    def __init__(self, app=None):
        """
        [4-1.1] 初始化调度器
        """
        self.app = app
        self.scheduler = scheduler
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        [4-1.2] 初始化Flask应用
        配置调度器并启动
        """
        self.app = app
        
        # [4-1.3] 配置调度器
        self.scheduler.configure(
            timezone=app.config.get('SCHEDULER_TIMEZONE', 'UTC'),
            job_defaults={
                'coalesce': False,
                'max_instances': 3,
                'misfire_grace_time': 30
            }
        )
        
        # [4-1.4] 启动调度器
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info(\"任务调度器已启动\")
        
        # [4-1.5] 应用关闭时停止调度器
        import atexit
        atexit.register(lambda: self.scheduler.shutdown())
    
    def add_task_job(self, task):
        """
        [4-1.6] 添加任务到调度器
        为运行中的任务创建定时job
        """
        if not task.can_execute():
            return False
        
        job_id = f"task_{task.id}"
        
        # [4-1.7] 移除已存在的job
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # [4-1.8] 添加新的定时job
        self.scheduler.add_job(
            func=self.execute_task,
            trigger=IntervalTrigger(seconds=task.interval_seconds),
            args=[task.id],
            id=job_id,
            name=f\"Task: {task.task_name}\",
            start_date=task.start_time,
            end_date=task.end_time,
            replace_existing=True
        )
        
        logger.info(f\"任务 {task.task_name} (ID: {task.id}) 已添加到调度器\")
        return True
    
    def remove_task_job(self, task_id):
        """
        [4-1.9] 从调度器移除任务
        暂停或停止任务时调用
        """
        job_id = f\"task_{task_id}\"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f\"任务 (ID: {task_id}) 已从调度器移除\")
    
    def execute_task(self, task_id):
        """
        [4-2] 执行单个任务
        调度器定时调用的核心执行方法
        """
        with self.app.app_context():
            try:
                # [4-2.1] 获取任务信息
                task = Task.query.get(task_id)
                if not task or not task.can_execute():
                    self.remove_task_job(task_id)
                    return
                
                # [4-2.2] 获取下一个待执行的文件
                file_to_execute = task.get_next_file()
                if not file_to_execute:
                    # 没有更多文件可执行，完成任务
                    task.complete_task()
                    self.remove_task_job(task_id)
                    logger.info(f\"任务 {task.task_name} 已完成，所有文件执行完毕\")
                    return
                
                # [4-2.3] 执行文件上传到目标网站
                success, response_data, error_message = self.upload_file_to_target(
                    file_to_execute, task.target_url, task.execution_method
                )
                
                if success:
                    # [4-2.4] 执行成功处理
                    file_to_execute.mark_as_executed()
                    file_to_execute.move_to_executed_folder()
                    task.increment_executed_count()
                    
                    # [4-2.5] 记录成功执行
                    TaskExecution.create_success_record(
                        task_id=task.id,
                        file_id=file_to_execute.id,
                        response_data=response_data
                    )
                    
                    logger.info(f\"文件 {file_to_execute.original_filename} 执行成功\")
                else:
                    # [4-2.6] 执行失败处理
                    TaskExecution.create_failed_record(
                        task_id=task.id,
                        file_id=file_to_execute.id,
                        error_message=error_message
                    )
                    
                    logger.error(f\"文件 {file_to_execute.original_filename} 执行失败: {error_message}\")
                
            except Exception as e:
                logger.error(f\"执行任务 {task_id} 时发生错误: {str(e)}\")
                
                # [4-2.7] 记录系统错误
                try:
                    task = Task.query.get(task_id)
                    if task:
                        task.fail_task()
                        self.remove_task_job(task_id)
                except Exception:
                    pass
    
    def upload_file_to_target(self, file_obj, target_url, method):
        """
        [4-3] 将文件内容上传到目标网站
        实现a_method的具体逻辑
        """
        try:
            # [4-3.1] 读取文件内容
            file_content = file_obj.read_content()
            
            # [4-3.2] 准备请求数据
            if method == 'a_method':
                # 实现a方法的具体逻辑
                payload = {
                    'content': file_content,
                    'filename': file_obj.original_filename,
                    'timestamp': datetime.utcnow().isoformat(),
                    'method': method
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'FileTaskManager/1.0'
                }
                
                # [4-3.3] 发送HTTP请求
                response = requests.post(
                    target_url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                # [4-3.4] 检查响应状态
                if response.status_code == 200:
                    return True, response.text, None
                else:
                    error_msg = f\"HTTP {response.status_code}: {response.text}\"
                    return False, None, error_msg
            
            else:
                # 其他方法的实现
                return False, None, f\"不支持的执行方法: {method}\"
        
        except requests.exceptions.Timeout:
            return False, None, \"请求超时\"
        except requests.exceptions.ConnectionError:
            return False, None, \"连接错误\"
        except requests.exceptions.RequestException as e:
            return False, None, f\"请求异常: {str(e)}\"
        except Exception as e:
            return False, None, f\"执行错误: {str(e)}\"
    
    def start_all_running_tasks(self):
        """
        [4-4] 启动所有运行中的任务
        系统重启时调用，恢复之前运行的任务
        """
        with self.app.app_context():
            running_tasks = Task.query.filter_by(status='running').all()
            
            for task in running_tasks:
                if task.can_execute():
                    self.add_task_job(task)
                    logger.info(f\"恢复运行任务: {task.task_name}\")
                else:
                    # 任务已过期，标记为完成
                    task.complete_task()
                    logger.info(f\"任务 {task.task_name} 已过期，标记为完成\")
    
    def get_scheduler_status(self):
        """
        [4-5] 获取调度器状态信息
        用于管理员监控
        """
        return {
            'running': self.scheduler.running,
            'jobs_count': len(self.scheduler.get_jobs()),
            'jobs': [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in self.scheduler.get_jobs()
            ]
        }

# [4-6] 全局调度器实例
task_scheduler = TaskScheduler()