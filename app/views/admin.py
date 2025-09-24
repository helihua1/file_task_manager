"""
[管理员视图控制器]
处理系统管理、用户监控、任务监控等管理功能
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.models.user import User
from app.models.task import Task
from app.models.file import File
from app.models.task_execution import TaskExecution
from app import db
from app.scheduler import task_scheduler

admin = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """
    [5] 管理员权限装饰器
    确保只有管理员可以访问管理功能
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('需要管理员权限', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """
    [5-1] 管理员仪表板
    显示系统整体运行状况和统计信息
    """
    # [5-1.1] 获取系统统计信息
    total_users = User.query.count()
    total_tasks = Task.query.count()
    running_tasks = Task.query.filter_by(status='running').count()
    total_files = File.query.count()
    executed_files = File.query.filter_by(is_executed=True).count()
    
    # [5-1.2] 获取最近活跃用户
    recent_users = User.query.filter(User.last_login.isnot(None))\
                            .order_by(User.last_login.desc())\
                            .limit(10).all()
    
    # [5-1.3] 获取运行中的任务
    active_tasks = Task.query.filter_by(status='running')\
                           .order_by(Task.updated_at.desc())\
                           .limit(10).all()
    
    # [5-1.4] 获取系统状态
    scheduler_status = task_scheduler.get_scheduler_status()
    
    system_stats = {
        'total_users': total_users,
        'total_tasks': total_tasks,
        'running_tasks': running_tasks,
        'total_files': total_files,
        'executed_files': executed_files,
        'pending_files': total_files - executed_files,
        'scheduler_running': scheduler_status['running'],
        'active_jobs': scheduler_status['jobs_count']
    }
    
    return render_template('admin/dashboard.html',
                         system_stats=system_stats,
                         recent_users=recent_users,
                         active_tasks=active_tasks,
                         scheduler_status=scheduler_status)

@admin.route('/users')
@login_required
@admin_required
def users():
    """
    [5-2] 用户管理页面
    显示所有用户信息和统计数据
    """
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    # [5-2.1] 构建查询条件
    query = User.query
    if search:
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.email.contains(search)
            )
        )
    
    # [5-2.2] 分页查询用户
    users = query.order_by(User.created_at.desc())\
                 .paginate(page=page, per_page=20, error_out=False)
    
    # [5-2.3] 为每个用户获取统计信息
    user_stats = {}
    for user in users.items:
        file_stats = user.get_upload_stats()
        task_stats = user.get_task_stats()
        execution_stats = TaskExecution.get_user_execution_stats(user.id)
        
        user_stats[user.id] = {
            **file_stats,
            **task_stats,
            **execution_stats
        }
    
    return render_template('admin/users.html', 
                         users=users, 
                         user_stats=user_stats,
                         search=search)

@admin.route('/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    """
    [5-3] 用户详情页面
    显示特定用户的详细信息和活动记录
    """
    user = User.query.get_or_404(user_id)
    
    # [5-3.1] 获取用户的任务列表
    user_tasks = Task.query.filter_by(user_id=user_id)\
                          .order_by(Task.created_at.desc()).all()
    
    # [5-3.2] 获取用户的文件列表
    user_files = File.query.filter_by(user_id=user_id)\
                          .order_by(File.upload_time.desc())\
                          .limit(50).all()
    
    # [5-3.3] 获取用户的执行记录
    execution_records = db.session.query(TaskExecution)\
                                 .join(Task, TaskExecution.task_id == Task.id)\
                                 .filter(Task.user_id == user_id)\
                                 .order_by(TaskExecution.execution_time.desc())\
                                 .limit(50).all()
    
    return render_template('admin/user_detail.html',
                         user=user,
                         user_tasks=user_tasks,
                         user_files=user_files,
                         execution_records=execution_records)

@admin.route('/tasks')
@login_required
@admin_required
def tasks():
    """
    [5-4] 任务监控页面
    显示所有任务的运行状态和监控信息
    """
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    
    # [5-4.1] 构建查询条件
    query = Task.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # [5-4.2] 分页查询任务
    tasks = query.order_by(Task.updated_at.desc())\
               .paginate(page=page, per_page=20, error_out=False)
    
    # [5-4.3] 获取任务统计信息
    task_counts = {
        'all': Task.query.count(),
        'running': Task.query.filter_by(status='running').count(),
        'pending': Task.query.filter_by(status='pending').count(),
        'completed': Task.query.filter_by(status='completed').count(),
        'failed': Task.query.filter_by(status='failed').count(),
        'paused': Task.query.filter_by(status='paused').count()
    }
    
    return render_template('admin/tasks.html',
                         tasks=tasks,
                         task_counts=task_counts,
                         status_filter=status_filter)

@admin.route('/tasks/<int:task_id>/control/<action>', methods=['POST'])
@login_required
@admin_required
def control_task(task_id, action):
    """
    [5-5] 任务控制操作
    管理员可以启动、暂停、停止任何用户的任务
    """
    task = Task.query.get_or_404(task_id)
    
    try:
        if action == 'start':
            if task.status in ['pending', 'paused']:
                task.start_task()
                task_scheduler.add_task_job(task)
                flash(f'任务 \"{task.task_name}\" 已启动', 'success')
            else:
                flash('只能启动待执行或已暂停的任务', 'warning')
                
        elif action == 'pause':
            if task.status == 'running':
                task.pause_task()
                task_scheduler.remove_task_job(task_id)
                flash(f'任务 \"{task.task_name}\" 已暂停', 'success')
            else:
                flash('只能暂停运行中的任务', 'warning')
                
        elif action == 'stop':
            if task.status in ['running', 'paused']:
                task.complete_task()
                task_scheduler.remove_task_job(task_id)
                flash(f'任务 \"{task.task_name}\" 已停止', 'success')
            else:
                flash('只能停止运行中或已暂停的任务', 'warning')
                
        else:
            flash('无效的操作', 'error')
            
    except Exception as e:
        flash(f'操作失败: {str(e)}', 'error')
    
    return redirect(url_for('admin.tasks'))

@admin.route('/system')
@login_required
@admin_required
def system():
    """
    [5-6] 系统状态页面
    显示系统运行状态、调度器状态等技术信息
    """
    # [5-6.1] 获取调度器详细状态
    scheduler_status = task_scheduler.get_scheduler_status()
    
    # [5-6.2] 获取数据库统计
    db_stats = {
        'users_count': User.query.count(),
        'tasks_count': Task.query.count(),
        'files_count': File.query.count(),
        'executions_count': TaskExecution.query.count()
    }
    
    # [5-6.3] 获取系统资源使用情况（简化版本）
    import psutil
    import os
    
    system_info = {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'python_version': f"{psutil.python_version()}",
        'process_id': os.getpid()
    }
    
    return render_template('admin/system.html',
                         scheduler_status=scheduler_status,
                         db_stats=db_stats,
                         system_info=system_info)

@admin.route('/api/system_status')
@login_required
@admin_required
def api_system_status():
    """
    [5-7] 系统状态API
    为前端实时更新提供数据接口
    """
    try:
        # [5-7.1] 获取实时任务统计
        task_stats = {
            'running': Task.query.filter_by(status='running').count(),
            'pending': Task.query.filter_by(status='pending').count(),
            'completed': Task.query.filter_by(status='completed').count(),
            'failed': Task.query.filter_by(status='failed').count()
        }
        
        # [5-7.2] 获取调度器状态
        scheduler_status = task_scheduler.get_scheduler_status()
        
        # [5-7.3] 获取最近执行记录
        recent_executions = TaskExecution.query\
                                       .order_by(TaskExecution.execution_time.desc())\
                                       .limit(5).all()
        
        executions_data = [
            {
                'id': execution.id,
                'task_id': execution.task_id,
                'status': execution.status,
                'execution_time': execution.execution_time.strftime('%H:%M:%S')
            }
            for execution in recent_executions
        ]
        
        return jsonify({
            'task_stats': task_stats,
            'scheduler_running': scheduler_status['running'],
            'active_jobs': scheduler_status['jobs_count'],
            'recent_executions': executions_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500