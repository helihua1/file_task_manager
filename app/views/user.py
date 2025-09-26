"""
[用户功能视图控制器]
处理用户文件上传、任务管理等核心功能
"""
import os
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
# from werkzeug.utils import secure_filename
from app.models.user import User
from app.models.file import File
from app.models.task import Task
from app.models.task_execution import TaskExecution
from app import db

user = Blueprint('user', __name__, url_prefix='/user')

def allowed_file(filename):
    """
    [2-1.1] 检查文件扩展名是否允许
    只允许上传txt文件
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def create_user_upload_dir(user_id):
    """
    [2-1.2] 创建用户专属上传目录
    为每个用户创建独立的文件存储目录
    """
    user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user_id))
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

@user.route('/dashboard')
@login_required
def dashboard():
    """
    [2-1] 用户仪表板
    显示用户的文件统计、任务统计和最近活动
    """
    # [2-1.3] 获取用户统计信息
    file_stats = current_user.get_upload_stats()
    task_stats = current_user.get_task_stats()
    
    # [2-1.4] 获取最近的任务
    recent_tasks = Task.query.filter_by(user_id=current_user.id)\
                            .order_by(Task.created_at.desc())\
                            .limit(5).all()
    
    # [2-1.5] 获取最近上传的文件
    recent_files = File.query.filter_by(user_id=current_user.id)\
                            .order_by(File.upload_time.desc())\
                            .limit(10).all()
    
    return render_template('user/dashboard.html',
                         file_stats=file_stats,
                         task_stats=task_stats,
                         recent_tasks=recent_tasks,
                         recent_files=recent_files)

@user.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_files():
    """
    [2-2] 文件上传处理
    GET: 显示文件上传页面
    POST: 处理批量文件上传
    """
    if request.method == 'POST':
        # [2-2.1] 检查是否有文件被上传
        if 'files' not in request.files:
            flash('请选择要上传的文件', 'error')
            return redirect(request.url)
        
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            flash('请选择要上传的文件', 'error')
            return redirect(request.url)
        
        # [2-2.2] 创建用户上传目录
        user_upload_dir = create_user_upload_dir(current_user.id)
        
        uploaded_count = 0
        failed_count = 0
        
        # [2-2.3] 批量处理上传的文件
        for file in files:
            if file and allowed_file(file.filename):
                try:
                    # [2-2.4] 生成安全的文件名
                    # original_filename = secure_filename(file.filename)
                    # file_extension = original_filename.rsplit('.', 1)[1].lower()
                    
                    # unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
                    # file_path = os.path.join(user_upload_dir, unique_filename)
                    original_filename = file.filename
                    file_path = os.path.join(user_upload_dir, original_filename)
                    
                    # [2-2.5] 保存文件到磁盘
                    file.save(file_path)
                    file_size = os.path.getsize(file_path)
                    
                    # [2-2.6] 保存文件信息到数据库
                    file_record = File(
                        user_id=current_user.id,
                        # filename=unique_filename,
                        original_filename=original_filename,
                        filename=original_filename,
                        file_path=file_path,
                        file_size=file_size
                    )
                    db.session.add(file_record)
                    uploaded_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    current_app.logger.error(f"文件上传失败: {file.filename}, 错误: {str(e)}")
            else:
                failed_count += 1
        
        # [2-2.7] 提交数据库事务
        try:
            db.session.commit()
            if uploaded_count > 0:
                flash(f'成功上传 {uploaded_count} 个文件', 'success')
            if failed_count > 0:
                flash(f'{failed_count} 个文件上传失败', 'warning')
        except Exception as e:
            db.session.rollback()
            flash('文件上传失败，请重试', 'error')
            current_app.logger.error(f"数据库保存失败: {str(e)}")
        
        return redirect(url_for('user.file_list'))
    
    return render_template('user/upload.html')

@user.route('/files')
@login_required
def file_list():
    """
    [2-3] 文件列表显示
    展示用户上传的所有文件，支持分页和筛选
    """
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    
    # [2-3.1] 构建查询条件
    query = File.query.filter_by(user_id=current_user.id)
    
    if status_filter == 'executed':
        query = query.filter_by(is_executed=True)
    elif status_filter == 'pending':
        query = query.filter_by(is_executed=False)
    
    # [2-3.2] 分页查询
    files = query.order_by(File.upload_time.desc())\
                 .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('user/files.html', files=files, status_filter=status_filter)

@user.route('/files/delete/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    """
    [2-4] 删除文件
    删除指定的文件记录和物理文件
    """
    file_record = File.query.filter_by(id=file_id, user_id=current_user.id).first()
    if not file_record:
        flash('文件不存在', 'error')
        return redirect(url_for('user.file_list'))
    
    try:
        file_record.delete_file()
        flash('文件删除成功', 'success')
    except Exception as e:
        flash('文件删除失败', 'error')
        current_app.logger.error(f"删除文件失败: {str(e)}")
    
    return redirect(url_for('user.file_list'))

@user.route('/tasks')
@login_required
def task_list():
    """
    [3-1] 任务列表显示
    展示用户创建的所有任务
    """
    tasks = Task.query.filter_by(user_id=current_user.id)\
                     .order_by(Task.created_at.desc()).all()
    
    return render_template('user/tasks.html', tasks=tasks)

@user.route('/tasks/create', methods=['GET', 'POST'])
@login_required
def create_task():
    """
    [3-2] 创建新任务
    GET: 显示任务创建表单
    POST: 保存新任务到数据库
    """
    if request.method == 'POST':
        task_name = request.form.get('task_name')
        target_url = request.form.get('target_url')
        execution_method = request.form.get('execution_method', 'a_method')
        interval_seconds = request.form.get('interval_seconds', type=int)
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        # [3-2.1] 验证输入数据
        if not all([task_name, target_url, interval_seconds, start_time_str]):
            flash('请填写所有必填字段', 'error')
            return render_template('user/create_task.html')
        
        if interval_seconds < 1:
            flash('执行间隔必须大于0秒', 'error')
            return render_template('user/create_task.html')
        
        try:
            # [3-2.2] 解析时间字符串
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = None
            if end_time_str:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
                if end_time <= start_time:
                    flash('结束时间必须晚于开始时间', 'error')
                    return render_template('user/create_task.html')
            
            # [3-2.3] 检查是否有可执行的文件
            pending_files_count = File.query.filter_by(
                user_id=current_user.id, 
                is_executed=False
            ).count()
            
            if pending_files_count == 0:
                flash('没有可执行的文件，请先上传文件', 'error')
                return redirect(url_for('user.upload_files'))
            
            # [3-2.4] 创建任务记录
            task = Task(
                user_id=current_user.id,
                task_name=task_name,
                target_url=target_url,
                execution_method=execution_method,
                interval_seconds=interval_seconds,
                start_time=start_time,
                end_time=end_time
            )
            
            db.session.add(task)
            db.session.commit()
            
            flash(f'任务 "{task_name}" 创建成功', 'success')
            return redirect(url_for('user.task_list'))
            
        except ValueError:
            flash('时间格式错误', 'error')
        except Exception as e:
            db.session.rollback()
            flash('任务创建失败，请重试', 'error')
            current_app.logger.error(f"创建任务失败: {str(e)}")
    
    return render_template('user/create_task.html')

@user.route('/tasks/<int:task_id>')
@login_required
def task_detail(task_id):
    """
    [3-3] 任务详情页面
    显示任务的详细信息和执行历史
    """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        flash('任务不存在', 'error')
        return redirect(url_for('user.task_list'))
    
    # [3-3.1] 获取任务执行历史
    execution_history = TaskExecution.get_task_execution_history(task_id)
    
    return render_template('user/task_detail.html', 
                         task=task, 
                         execution_history=execution_history)

@user.route('/tasks/<int:task_id>/start', methods=['POST'])
@login_required
def start_task(task_id):
    """
    [3-4] 启动任务
    将任务状态设置为运行中
    """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        flash('任务不存在', 'error')
        return redirect(url_for('user.task_list'))
    
    if task.status == 'running':
        flash('任务已在运行中', 'warning')
    else:
        task.start_task()
        flash(f'任务 "{task.task_name}" 已启动', 'success')
    
    return redirect(url_for('user.task_detail', task_id=task_id))

@user.route('/tasks/<int:task_id>/pause', methods=['POST'])
@login_required
def pause_task(task_id):
    """
    [3-5] 暂停任务
    将任务状态设置为暂停
    """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        flash('任务不存在', 'error')
        return redirect(url_for('user.task_list'))
    
    if task.status == 'running':
        task.pause_task()
        flash(f'任务 "{task.task_name}" 已暂停', 'success')
    else:
        flash('只能暂停正在运行的任务', 'warning')
    
    return redirect(url_for('user.task_detail', task_id=task_id))

@user.route('/api/task_status/<int:task_id>')
@login_required
def get_task_status(task_id):
    """
    [3-6] 获取任务状态API
    用于前端实时更新任务状态
    """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify(task.get_task_info())