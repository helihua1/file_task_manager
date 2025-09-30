"""
[任务调度系统]
使用APScheduler实现定时任务的调度和执行
"""
import requests
import logging
import threading
import time
from datetime import datetime, time as dt_time, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.models.task import Task
from app.models.file import File
from app.models.task_execution import TaskExecution
from app.models.url_context import UrlUpdateContext
from app import db
import test
from app.models.url_context import url_update_context
# [4] 任务调度器初始化
scheduler = BackgroundScheduler()
logger = logging.getLogger(__name__)

# 全局session锁，用于管理同一网站的并发访问
session_locks = {}
session_lock = threading.Lock()
# from sqlalchemy.orm import sessionmaker
# SessionLocal = sessionmaker(bind=db.engine)

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
                'max_instances': 10,  # 增加最大实例数
                'misfire_grace_time': 30
            }
        )
        
        # [4-1.4] 启动调度器
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("任务调度器已启动")
        
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

        # todo 每个人可能有多个任务不能直接去除
        job_id = f"task_{task.id}"
        
        # [4-1.7] 移除已存在的job
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # [4-1.8] 根据任务配置选择触发器
        if task.daily_start_time:
            # 使用cron触发器，每天在指定时间执行
            trigger = CronTrigger(
                hour=task.daily_start_time.hour,
                minute=task.daily_start_time.minute,
                start_date=task.start_time,
                end_date=task.end_time
            )
        else:
            # # 使用间隔触发器
            # trigger = IntervalTrigger(
            #     seconds=task.interval_seconds,
            #     # start_date=task.start_time,
            #     end_date=task.end_time
            # )

            # 2秒后执行一次
            trigger = DateTrigger(run_date=datetime.now() + timedelta(seconds=2))
            

        # [4-1.9] 添加新的定时job
        self.scheduler.add_job(
            func=self.execute_task,
            trigger=trigger,
            args=[task.id],
            id=job_id,
            name=f"Task: {task.task_name}",
            replace_existing=True
        )
        
        logger.info(f"任务 {task.task_name} (ID: {task.id}) 已添加到调度器")
        return True
    
    def remove_task_job(self, task_id):
        """
        [4-1.10] 从调度器移除任务
        暂停或停止任务时调用
        """
        # todo 增加is_excuting字段要改回0！！！
        job_id = f"task_{task_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"任务 (ID: {task_id}) 已从调度器移除")

    def execute_task(self, task_id):
        """
        [4-2] 执行单个任务
        调度器定时调用的核心执行方法
        """

        '''
        执行器机制：APScheduler默认使用ThreadPoolExecutor，每个job在独立的线程中执行。
        执行方式：每个 execute_task 在 APScheduler 的线程池中运行
        并发控制：受 max_instances: 10 限制
        职责：获取文件列表，调用文件上传逻辑
        '''
        with self.app.app_context():
            try:
                # [4-2.1] 获取任务信息
                task = Task.query.get(task_id)
                if not task or not task.can_execute():
                    self.remove_task_job(task_id)
                    return
                
                # [4-2.2] 获取目标URL列表
                target_urls = task.target_url.split(',')
                
                # [4-2.3] 安全获取要执行的文件（防止文件竞争）
                files_to_execute = self.get_files_safely(task, target_urls)
                
                if not files_to_execute:
                    # 没有更多文件可执行，暂停任务
                    task.pause_task()
                    self.remove_task_job(task_id)
                    logger.info(f"任务 {task.task_name} 暂停，没有足够文件可以被执行了！！！！")
                    return
                
                # [4-2.4] 并行执行文件上传到多个目标网站
                self.execute_parallel_uploads(task, files_to_execute, target_urls)
                
            except Exception as e:
                logger.error(f"执行任务 {task_id} 时发生错误: {str(e)}")
                
                # [4-2.5] 记录系统错误
                try:
                    task = Task.query.get(task_id)
                    if task:
                        task.fail_task()
                        self.remove_task_job(task_id)
                except Exception:
                    pass

    def get_files_safely(self, task, target_urls):
        """
        [4-2.3.1] 安全获取文件列表
        使用数据库锁防止文件竞争
        """
        from app.models.file import File
        import threading
        import time
        
        files_to_execute = []
        total_files_needed = task.daily_execution_count * len(target_urls)
        
        # 使用数据库事务确保原子性
        for _ in range(total_files_needed):
            file_obj = self.get_next_file_atomically(task)
            if file_obj:
                files_to_execute.append(file_obj)
            else:
                logger.info(f"没有更多文件可执行，暂停任务 {task.task_name}")
                print(f"--------------------------------没有更多文件可执行，暂停任务 {task.task_name}")
                task.pause_task()
                self.remove_task_job(task.id)
                break
        
        return files_to_execute

    def get_next_file_atomically(self, task):
        """
        [4-2.3.2] 原子性获取下一个文件
        使用数据库锁和事务确保文件不会被重复分配
        """
        from app.models.file import File
        import os

        # 获取数据库会话
        def get_session_local():
            """动态获取 SessionLocal，确保在应用上下文中创建"""
            from sqlalchemy.orm import sessionmaker
            return sessionmaker(bind=db.engine)

        dbsession = get_session_local()()

        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 使用普通事务，不使用嵌套事务
                with dbsession.begin():
                    # 使用SELECT FOR UPDATE锁定文件记录
                    if task.source_folder:
                        linux_pattern = f'%{os.sep}{task.source_folder}{os.sep}%'
                        windows_pattern = f'%\\\\{task.source_folder}\\\\%'

                        # FOR UPDATE是 行级锁
                        sql = """
                        SELECT * FROM files 
                        WHERE user_id = :user_id 
                        AND is_executed = 0 
                        AND is_executing = 0
                        AND (file_path LIKE :linux_pattern OR file_path LIKE :windows_pattern)
                        ORDER BY id ASC 
                        LIMIT 1
                        FOR UPDATE
                        """
                        
                        result = dbsession.execute(
                            db.text(sql), 
                            {
                                'user_id': task.user_id,
                                'linux_pattern': linux_pattern,
                                'windows_pattern': windows_pattern
                            }
                        ).fetchone()

                    if result:
                        file_id = result.id
                        
                        # 更新文件状态为正在处理
                        update_sql = """
                        UPDATE files 
                        SET is_executing = 1
                        WHERE id = :file_id AND is_executed = 0 AND is_executing = 0
                        """
                        
                        update_result = dbsession.execute(
                            db.text(update_sql), 
                            {'file_id': file_id}
                        )
                        
                        if update_result.rowcount > 0:
                            # 事务会自动提交，返回文件对象
                            return File.query.get(file_id)
                        else:
                            # 文件已被其他任务获取，重试
                            retry_count += 1
                            time.sleep(0.1)
                            continue
                    else:
                        return None
                        
            except Exception as e:
                logger.error(f"获取文件时发生错误: {str(e)}")
                retry_count += 1
                time.sleep(0.1)
                continue
        
        return None

    def execute_parallel_uploads(self, task, files, target_urls):
        """
        [4-3] 并行执行文件上传
        为每个目标URL创建线程，但同一网站的请求会串行执行
        """
        import threading



        def upload_to_target(target_url, file_objs):
            """
            上传文件到指定目标URL
            """
            # 在子线程中创建应用上下文
                # 想象Flask应用上下文就像一个"工作环境"，在这个环境里你才能：
                # 连接数据库
                # 使用Flask的ORM功能
                # 访问应用配置
                # 没有这个环境，就像在没有网络的地方尝试上网一样，会报错。
                # 所以 with self.app.app_context(): 就是在子线程中"搭建"这个工作环境，让数据库操作能够正常进行
            def get_session_local():
                """动态获取 SessionLocal，确保在应用上下文中创建"""
                from sqlalchemy.orm import sessionmaker
                return sessionmaker(bind=db.engine)
            with self.app.app_context():

                # 第一个括号 ()：调用 get_session_local() 函数，返回一个 sessionmaker 对象
                # 第二个括号 ()：调用返回的 sessionmaker 对象，创建一个新的数据库会话
                dbsession = get_session_local()()

                try:
                    # 解析URL获取网站信息
                    url_parts = target_url.split('栏目值:')
                    if len(url_parts) != 2:
                        logger.error(f"URL格式错误: {target_url}")
                        return False, None, "URL格式错误"
                    
                    root_url = url_parts[0]
                    menu_value = url_parts[1]
                    
                    # 获取网站配置信息，返回UrlUpdateContext对象实例
                    url_context = UrlUpdateContext.query.filter_by(root_url=root_url).first()
                    if not url_context:
                        logger.error(f"未找到URL配置: {root_url}")
                        return False, None, "未找到URL配置"
                    
                    # 使用网站锁确保同一网站的请求串行执行
                    with self.get_site_lock(root_url):

                        # 创建session，并且登录

                        # [4-5.1] 创建session上下文
                        
                        session = requests.Session()
                        upload_date = url_update_context(session, url_context.root_url, url_context.suffix, url_context.username, url_context.password)

                        # [4-5.2] 执行upload_before逻辑
                        zixun_page = test.upload_before(upload_date)


                        if  zixun_page.status_code != 200:
                            return False, None, f"upload_before执行失败 {zixun_page.status_code}"

                        # 循环上传文件
                        for file_obj_main_thread in file_objs:
                            try:
                                file_obj_main_thread.id
                                file_obj = dbsession.query(File).filter_by(id=file_obj_main_thread.id).first()
                                print(f"数据库线程得到的filename:{file_obj.filename}")
                                #  读取文件内容
                                file_content = file_obj.read_content()
                                file_title = file_obj.original_filename.replace('.txt', '')
                                
                                
                                # [4-5.3] 执行upload逻辑
                                status_code = test.upload(session, zixun_page, upload_date.base_url, menu_value, file_title, file_content)
                                time.sleep(task.interval_seconds)
                            except Exception as e:
                                # f"执行错误: {str(e)}" 是在 upload_to_target 函数内部，这个函数作为线程目标函数运行。线程的返回值不会被主线程捕获或处理。
                                print(f"执行错误: {str(e)}")
                                return False, None, f"执行错误: {str(e)}"
                                
                                
                            if status_code == 200:
                                try:

                                    # 标记文件为已执行
                                    file_obj.is_executed = True
                                    file_obj.is_executing = False  # 重置正在处理状态
                                    file_obj.executed_at = datetime.utcnow()
                                    
                                    # 移动文件到已执行文件夹
                                    file_obj.move_to_executed_folder()
                                    
                                    # 增加已执行计数
                                    task.executed_files_count += 1
                                    task.updated_at = datetime.utcnow()
                                    
                                    # 创建执行记录
                                    execution_record = TaskExecution(
                                        task_id=task.id,
                                        file_id=file_obj.id,
                                        status='success',
                                        response_data=status_code
                                    )
                                    dbsession.add(execution_record)
                                    
                                    # 一次性提交所有更改，在 Flask-SQLAlchemy 中，所有通过 Model.query 查询得到的对象都会被当前的 db.session 自动跟踪。当你修改这些对象的属性时，session 会将这些对象标记为 "dirty"（需要更新）。调用 commit() 时，session 会生成相应的 SQL 语句来更新所有被修改的对象
                                    dbsession.commit()
                                    
                                    logger.info(f"文件 {file_obj.original_filename} 上传到 {root_url} 成功")
                                    
                                except Exception as e:
                                    print(f"数据库操作失败: {str(e)}，回滚")
                                    db.session.rollback()
                                    logger.error(f"数据库操作失败: {str(e)}")
                            else:
                                # 记录失败执行
                                TaskExecution.create_failed_record(
                                    task_id=task.id,
                                    file_id=file_obj.id,
                                    error_message=status_code
                                )
                                
                                logger.error(f"文件 {file_obj.original_filename} 上传到 {root_url} 失败: {status_code}")


                
                except Exception as e:
                    logger.error(f"上传文件到 {target_url} 时发生错误: {str(e)}")
                    return False, None, str(e)
                finally:
                    dbsession.close()
        
        # 创建线程列表
        threads = []
        

        # 按比例分配文件到不同目标URL
        files_per_target = len(files) // len(target_urls)
        # 为每个目标URL和文件组合创建线程
        for i, target_url in enumerate(target_urls):
            start_idx = i * files_per_target
            end_idx = start_idx + files_per_target
            target_files = files[start_idx:end_idx]
  

            # todo 后续改为： 使用线程池而不是创建新线程

            # 创建上传线程
            thread = threading.Thread(
                target=upload_to_target,
                args=(target_url, target_files),
                name=f"Upload-{task.id}-{target_url}"
            )
            
            threads.append(thread)
            thread.start()

        # 前面创建了多个线程来并行上传文件到不同网站
        # 每个线程都在独立执行上传任务
        # join() 确保主线程等待所有上传线程都完成
        # 只有当所有文件都上传完成后，方法才会返回
        for thread in threads:
            thread.join()
    
    def get_site_lock(self, root_url):
        """
        [4-4] 获取网站锁
        确保同一网站的请求串行执行
        """
        with session_lock:
            if root_url not in session_locks:
                session_locks[root_url] = threading.Lock()
            return session_locks[root_url]
    


    def start_all_running_tasks(self):
        """
        [4-8] 启动所有运行中的任务
        系统重启时调用，恢复之前运行的任务
        """
        with self.app.app_context():
            running_tasks = Task.query.filter_by(status='running').all()
            
            for task in running_tasks:
                if task.can_execute():
                    self.add_task_job(task)
                    logger.info(f"恢复运行任务: {task.task_name}")
                else:
                    # 任务已过期，标记为完成
                    task.complete_task()
                    logger.info(f"任务 {task.task_name} 已过期，标记为完成")
    
    def get_scheduler_status(self):
        """
        [4-9] 获取调度器状态信息
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

# [4-10] 全局调度器实例
task_scheduler = TaskScheduler()