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
from app.models.url_context import UrlUpdateContext, UrlMenu
import shutil
user = Blueprint('user', __name__, url_prefix='/user')
from app.scheduler import task_scheduler

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

def get_user_folders(user_id):
    """
    获取用户的所有文件夹
    返回用户目录下的所有文件夹列表
    """
    user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user_id))
    if not os.path.exists(user_dir):
        return []
    
    folders = []
    for item in os.listdir(user_dir):
        item_path = os.path.join(user_dir, item)
        if os.path.isdir(item_path):
            folders.append(item)
    return sorted(folders)

def create_user_folder(user_id, folder_name):
    """
    为用户创建新文件夹
    只允许单层文件夹，不允许嵌套
    """
    user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user_id))
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    
    folder_path = os.path.join(user_dir, folder_name)
    if os.path.exists(folder_path):
        return False, "文件夹已存在"
    
    try:
        os.makedirs(folder_path)
        return True, "文件夹创建成功"
    except Exception as e:
        return False, f"创建失败: {str(e)}"

def delete_user_folder(user_id, folder_name):
    """
    删除用户文件夹
    只能删除空文件夹
    """
    user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user_id))
    folder_path = os.path.join(user_dir, folder_name)
    
    if not os.path.exists(folder_path):
        return False, "文件夹不存在"
    
    try:
        # # 检查文件夹是否为空
        # if os.listdir(folder_path):
        #     return False, "只能删除空文件夹"
        
        # os.rmdir(folder_path)
        shutil.rmtree(folder_path)
        return True, "文件夹删除成功"
    except Exception as e:
        return False, f"删除失败: {str(e)}"

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

        # 传文件四：
        # request.files.getlist('files') 从HTTP请求中获取文件流
        # Werkzeug会将上传的数据存储在临时文件或内存缓冲区中
        # 返回的 file 对象是 FileStorage 类型，它是一个类文件对象（file-like object）
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            flash('请选择要上传的文件', 'error')
            return redirect(request.url)
        
        # [2-2.2] 获取目标文件夹
        target_folder = request.form.get('target_folder', '')
        user_upload_dir = create_user_upload_dir(current_user.id)
        
        # 如果指定了文件夹，使用该文件夹路径
        if target_folder:
            target_path = os.path.join(user_upload_dir, target_folder)
            if not os.path.exists(target_path):
                flash('指定的文件夹不存在', 'error')
                return redirect(request.url)
        else:
            target_path = user_upload_dir
        
        uploaded_count = 0
        failed_count = 0
        
        # [2-2.3] 批量处理上传的文件
        for file in files:
            if file and allowed_file(file.filename):
                try:
                    # 只保留文件名，去除可能的路径信息
                    original_filename = os.path.basename(file.filename)
                    file_path = os.path.join(target_path, original_filename)
                    
                    # [2-2.5] 保存文件到磁盘
                    file.save(file_path)    # 核心IO操作
                    file_size = os.path.getsize(file_path)
                    
                    # [2-2.6] 保存文件信息到数据库
                    file_record = File(
                        user_id=current_user.id,
                        original_filename=original_filename,
                        filename=original_filename,
                        file_path=file_path,
                        file_size=file_size,
                        folder=target_folder
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
    
    # GET请求时获取用户文件夹列表
    user_folders = get_user_folders(current_user.id)
    return render_template('user/upload.html', user_folders=user_folders)

@user.route('/api/create_folder', methods=['POST'])
@login_required
def create_folder():
    """
    创建新文件夹API
    """
    folder_name = request.form.get('folder_name', '').strip()
    
    if not folder_name:
        return jsonify({'success': False, 'message': '文件夹名称不能为空'})
    
    # 验证文件夹名称（不允许包含特殊字符）
    import re
    if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fa5_-]+$', folder_name):
        return jsonify({'success': False, 'message': '文件夹名称只能包含字母、数字、中文、下划线和连字符'})
    
    success, message = create_user_folder(current_user.id, folder_name)
    return jsonify({'success': success, 'message': message})

@user.route('/api/delete_folder', methods=['POST'])
@login_required
def delete_folder():
    """
    删除文件夹API
    """
    folder_name = request.form.get('folder_name', '').strip()
    
    if not folder_name:
        return jsonify({'success': False, 'message': '文件夹名称不能为空'})
    
    success, message = delete_user_folder(current_user.id, folder_name)
    return jsonify({'success': success, 'message': message})

@user.route('/api/get_folders')
@login_required
def get_folders():
    """
    获取用户文件夹列表API
    """
    folders = get_user_folders(current_user.id)
    return jsonify({'folders': folders})

@user.route('/files')
@login_required
def file_list():
    """
    [2-3] 文件列表显示
    按文件夹分组展示用户上传的所有文件，显示文件夹统计信息
    """
    status_filter = request.args.get('status', 'all')
    
    # [2-3.1] 获取所有文件并按文件夹分组
    query = File.query.filter_by(user_id=current_user.id)
    
    if status_filter == 'executed':
        query = query.filter_by(is_executed=True)
    elif status_filter == 'pending':
        query = query.filter_by(is_executed=False)
    
    all_files = query.order_by(File.folder.asc(), File.upload_time.desc()).all()
    
    # [2-3.2] 按文件夹分组
    folders_data = {}
    for file in all_files:
        folder_name = file.folder if file.folder else '根目录'
        
        if folder_name not in folders_data:
            folders_data[folder_name] = {
                'files': [],
                'total_count': 0,
                'executed_count': 0,
                'pending_count': 0
            }
        
        folders_data[folder_name]['files'].append(file)
        folders_data[folder_name]['total_count'] += 1
        
        if file.is_executed:
            folders_data[folder_name]['executed_count'] += 1
        else:
            folders_data[folder_name]['pending_count'] += 1
    
    return render_template('user/files.html', 
                         folders_data=folders_data, 
                         status_filter=status_filter)

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
    # 获取过滤参数
    filter_name = request.args.get('filter_name', '').strip()
    
    # 获取URL上下文数据
    url_contexts_query = UrlUpdateContext.query
    if filter_name:
        url_contexts_query = url_contexts_query.filter(UrlUpdateContext.name.like(f'%{filter_name}%'))
    url_contexts = url_contexts_query.all()
    
    # 获取用户文件夹列表
    user_folders = get_user_folders(current_user.id)
    
    if request.method == 'POST':
        task_name = request.form.get('task_name')
        target_urls = request.form.getlist('target_url')  # 改为获取多个URL
        execution_method = request.form.get('execution_method', 'a_method')
        interval_seconds = request.form.get('interval_seconds', type=int)
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        # 新增字段
        source_folder = request.form.get('source_folder')
        backup_folders_list = request.form.getlist('backup_folders')  # 获取备用文件夹列表
        daily_start_time_str = request.form.get('daily_start_time')
        daily_execution_count = request.form.get('daily_execution_count', type=int, default=1)
        
        # [3-2.1] 验证输入数据
        if not all([task_name, target_urls, interval_seconds, start_time_str, source_folder]):
            flash('请填写所有必填字段', 'error')
            return render_template('user/create_task.html', 
                                 url_contexts=url_contexts, 
                                 user_folders=user_folders,
                                 filter_name=filter_name)
        
        if interval_seconds < 1:
            flash('执行间隔必须大于0秒', 'error')
            return render_template('user/create_task.html', 
                                 url_contexts=url_contexts, 
                                 user_folders=user_folders,
                                 filter_name=filter_name)
        
        if daily_execution_count < 1:
            flash('每日执行数量必须大于0', 'error')
            return render_template('user/create_task.html', 
                                 url_contexts=url_contexts, 
                                 user_folders=user_folders,
                                 filter_name=filter_name)
        
        try:
            # [3-2.2] 解析时间字符串
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = None
            if end_time_str:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
                if end_time <= start_time:
                    flash('结束时间必须晚于开始时间', 'error')
                    return render_template('user/create_task.html', 
                                         url_contexts=url_contexts, 
                                         user_folders=user_folders,
                                         filter_name=filter_name)
            
            # 解析每日开始时间
            daily_start_time = None
            if daily_start_time_str:
                daily_start_time = datetime.strptime(daily_start_time_str, '%H:%M').time()
            
            # [3-2.3] 检查是否有可执行的文件

            # #             # [3-2.3] 检查是否有可执行的文件
            # pending_files_query = File.query.filter_by(
            #     user_id=current_user.id,
            #     is_executed=False
            # ).filter(
            #     db.or_(
            #         File.file_path.like(f'%/{source_folder}/%'),  # Linux/Mac路径
            #         File.file_path.like(r'%\\\\' +f'{source_folder}' + r'\\\\%')  # Windows路径
            #     )
            # )
            
            # # 获取查询结果数量
            # # 获取查询结果
            # pending_files = pending_files_query.all()
            # print(pending_files_query)
            # pending_files_count = len(pending_files)
            
            # # 打印生成的 SQL（移到count()之后）
            # print(str(pending_files_query.statement.compile(compile_kwargs={"literal_binds": True})))
            # 
            # 上面方式查询 结果为0 
            # 使用原生SQL查询
            sql = """
SELECT COUNT(*) as count 
FROM files 
WHERE user_id = :user_id 
AND is_executed = false 
AND (file_path LIKE :path1 OR file_path LIKE :path2)
"""

            # 构建路径参数
            path1 = f'%/{source_folder}/%'  # Linux/Mac路径
            path2 = f'%\\\\{source_folder}\\\\%'  # Windows路径

            # 执行原生SQL查询
            result = db.session.execute(db.text(sql), {
                'user_id': current_user.id,
                'path1': path1,
                'path2': path2
            }).fetchone()

            pending_files_count = result.count if result else 0

            print(f"SQL查询: {sql}")
            print(f"参数: user_id={current_user.id}, path1={path1}, path2={path2}")
            print(f"查询结果: {pending_files_count}")
            
  
            
            if pending_files_count == 0:
                flash(f'指定文件夹 "{source_folder}" 中没有可执行的文件，请先上传文件', 'error')
                return render_template('user/create_task.html', 
                                     url_contexts=url_contexts, 
                                     user_folders=user_folders,
                                     filter_name=filter_name)
            
            # [3-2.4] 创建任务记录
            import json
            target_url = ','.join(target_urls)  # 用逗号分隔存储多个URL
            
            # 过滤备用文件夹：去除与主文件夹相同的文件夹
            filtered_backup_folders = [f for f in backup_folders_list if f != source_folder]
            backup_folders_json = json.dumps(filtered_backup_folders) if filtered_backup_folders else None
            
            task = Task(
                user_id=current_user.id,
                task_name=task_name,
                target_url=target_url,
                execution_method=execution_method,
                interval_seconds=interval_seconds,
                start_time=start_time,
                end_time=end_time,
                source_folder=source_folder,
                backup_folders=backup_folders_json,
                daily_start_time=daily_start_time,
                daily_execution_count=daily_execution_count,
                # total_files_count=pending_files_count
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
    
    return render_template('user/create_task.html',
                         url_contexts=url_contexts,
                         user_folders=user_folders,
                         filter_name=filter_name)

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
        task_scheduler.add_task_job(task)

    
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
@user.route('/url_management')
@login_required
def url_management():
    """
    URL管理页面
    显示已添加的URL列表和添加新URL的界面
    """
    import json
    
    # 获取所有URL上下文数据
    url_contexts = UrlUpdateContext.query.all()
    
    # 获取用户的批量查询结果
    from app.models.url_context import BatchUrlFind
    batch_results = BatchUrlFind.query.filter_by(user_id=current_user.id).all()
    
    # 转换格式以兼容前端
    batch_results_data = []
    for result in batch_results:
        menu_data = []
        if result.menu_data:
            try:
                menu_data = json.loads(result.menu_data)
            except:
                menu_data = []
        
        batch_results_data.append({
            'name': result.name,
            'root_url': result.root_url,
            'suffix': result.suffix,
            'username': result.username,
            'password': result.password,
            'status': result.status,
            'error': result.error_message,
            'menu_count': result.menu_count,
            'menu_data': menu_data
        })
    
    # 从session中获取临时菜单数据
    from flask import session as flask_session
    menu_data = flask_session.get('temp_menu_data')
    url_data = flask_session.get('temp_url_data')
    
    return render_template('user/url_management.html', 
                         url_contexts=url_contexts,
                         batch_results=batch_results_data,
                         menu_data=menu_data,
                         url_data=url_data)

@user.route('/api/test_url_menu', methods=['POST'])
@login_required
def test_url_menu():
    """
    测试URL菜单获取
    调用test.py中的get_menu方法
    """
    print('开始检索')
    try:
        # 从表单数据获取参数
        name = request.form.get('name')
        root_url = request.form.get('root_url')
        suffix = request.form.get('suffix') 
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not all([root_url, suffix, username, password]):
            flash('所有字段都是必填的', 'error')
            return redirect(url_for('user.url_management'))
        
        # 导入测试模块
        import test
        from app.models.url_context import url_update_context
        import requests
        
        # 创建会话和上下文
        session = requests.Session()
        upload_context = url_update_context(session, root_url, suffix, username, password)
        
        # 获取菜单数据
        menu_data = test.get_menu(upload_context)
        
        if menu_data:
            # 将菜单数据存储到session中，供后续添加使用
            from flask import session as flask_session
            flask_session['temp_menu_data'] = menu_data
            flask_session['temp_url_data'] = {
                'name': name,
                'root_url': root_url,
                'suffix': suffix,
                'username': username,
                'password': password
            }
            flash(f'成功获取到 {len(menu_data)} 个菜单项', 'success')
            # 重定向回原页面，但带上数据
            return redirect(url_for('user.url_management'))
        else:
            flash('未能获取菜单数据', 'error')
            return redirect(url_for('user.url_management'))
            
    except Exception as e:
        flash(f'检索失败: {str(e)}', 'error')
        return redirect(url_for('user.url_management'))

@user.route('/confirm_url_menu')
@login_required
def confirm_url_menu():
    """
    确认菜单页面
    显示获取到的菜单数据，让用户确认是否添加
    """
    from flask import session as flask_session
    menu_data = flask_session.get('temp_menu_data')
    url_data = flask_session.get('temp_url_data')
    
    if not menu_data or not url_data:
        flash('没有可确认的菜单数据', 'error')
        return redirect(url_for('user.url_management'))
    
    return render_template('user/confirm_menu.html',
                         menu_data=menu_data,
                         url_data=url_data)

@user.route('/add_url_context', methods=['POST'])
@login_required
def add_url_context():
    """
    添加URL上下文到数据库
    保存URL信息和对应的菜单数据
    """
    try:
        from flask import session as flask_session
        menu_data = flask_session.get('temp_menu_data')
        
        # 从表单获取数据
        name = request.form.get('name')
        root_url = request.form.get('root_url')
        suffix = request.form.get('suffix')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not all([root_url, suffix, username, password]):
            flash('缺少必要参数', 'error')
            return redirect(url_for('user.url_management'))
        
        if not menu_data:
            flash('没有可添加的菜单数据', 'error')
            return redirect(url_for('user.url_management'))
        
        # 检查是否已存在相同的URL上下文
        existing = UrlUpdateContext.query.filter_by(
            root_url=root_url, 
            suffix=suffix
        ).first()
        
        if existing:
            flash('该URL上下文已存在', 'error')
            return redirect(url_for('user.url_management'))
        
        # 创建新的URL上下文
        url_context = UrlUpdateContext(
            name=name,
            root_url=root_url,
            suffix=suffix,
            username=username,
            password=password
        )
        db.session.add(url_context)
        db.session.flush()  # 获取ID
        
        # 添加菜单数据
        for menu_item in menu_data:
            menu_value = menu_item[0]
            menu_text = menu_item[1]
            
            url_menu = UrlMenu(
                context_id=url_context.id,
                menu_value=menu_value,
                menu_text=menu_text
            )
            db.session.add(url_menu)
        
        db.session.commit()
        
        # 清除临时数据
        flask_session.pop('temp_menu_data', None)
        flask_session.pop('temp_url_data', None)
        
        flash('URL上下文添加成功', 'success')
        return redirect(url_for('user.url_management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'添加失败: {str(e)}', 'error')
        return redirect(url_for('user.url_management'))

@user.route('/delete_url_context/<int:context_id>', methods=['POST'])
@login_required
def delete_url_context(context_id):
    """
    删除URL上下文
    根据context_id删除URL上下文和关联的菜单数据
    """
    try:
        # 查找URL上下文
        url_context = UrlUpdateContext.query.get(context_id)
        if not url_context:
            flash('URL上下文不存在', 'error')
            return redirect(url_for('user.url_management'))
        
        # 删除URL上下文（由于cascade='all, delete-orphan'，关联的菜单会自动删除）
        db.session.delete(url_context)
        db.session.commit()
        
        flash('URL上下文删除成功', 'success')
        return redirect(url_for('user.url_management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败: {str(e)}', 'error')
        return redirect(url_for('user.url_management'))

@user.route('/update_url_context_name/<int:context_id>', methods=['POST'])
@login_required
def update_url_context_name(context_id):
    """
    更新URL上下文的名称
    """
    try:
        # 查找URL上下文
        url_context = UrlUpdateContext.query.get(context_id)
        if not url_context:
            flash('URL上下文不存在', 'error')
            return redirect(url_for('user.url_management'))
        
        # 获取新的名称
        new_name = request.form.get('name', '').strip()
        
        # 更新名称
        url_context.name = new_name if new_name else None
        db.session.commit()
        
        flash('名称更新成功', 'success')
        return redirect(url_for('user.url_management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'更新失败: {str(e)}', 'error')
        return redirect(url_for('user.url_management'))

@user.route('/batch_upload_excel', methods=['POST'])
@login_required
def batch_upload_excel():
    """
    批量上传Excel文件处理
    读取Excel文件，解析每行数据，获取菜单数据
    """
    try:
        # 检查是否有文件上传
        if 'excel_file' not in request.files:
            flash('请选择Excel文件', 'error')
            return redirect(url_for('user.url_management'))
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('请选择Excel文件', 'error')
            return redirect(url_for('user.url_management'))
        
        # 检查文件扩展名
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            flash('请上传Excel文件(.xlsx或.xls格式)', 'error')
            return redirect(url_for('user.url_management'))
        
        # 导入pandas处理Excel
        import pandas as pd
        import io
        import test
        from app.models.url_context import url_update_context, BatchUrlFind
        import requests
        import json
        
        # 读取Excel文件
        file_content = file.read()
        df = pd.read_excel(io.BytesIO(file_content))
        
        # 检查列数
        if len(df.columns) < 5:
            flash('Excel文件格式错误：需要至少5列数据', 'error')
            return redirect(url_for('user.url_management'))
        
        # 先清除用户之前的批量查询记录
        BatchUrlFind.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        # 处理每行数据
        for index, row in df.iterrows():
            try:
                # 获取每行数据
                name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else f'未命名_{index+1}'
                root_url = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
                suffix = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ''
                username = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ''
                password = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ''
                
                # 验证必要字段
                if not all([root_url, suffix, username, password]):
                    batch_record = BatchUrlFind(
                        user_id=current_user.id,
                        name=name,
                        root_url=root_url,
                        suffix=suffix,
                        username=username,
                        password=password,
                        status='error',
                        error_message='缺少必要字段',
                        menu_count=0
                    )
                    db.session.add(batch_record)
                    continue
                
                # 检查是否已存在相同的URL上下文
                existing = UrlUpdateContext.query.filter_by(
                    root_url=root_url, 
                    suffix=suffix
                ).first()
                
                if existing:
                    batch_record = BatchUrlFind(
                        user_id=current_user.id,
                        name=name,
                        root_url=root_url,
                        suffix=suffix,
                        username=username,
                        password=password,
                        status='error',
                        error_message='URL上下文已存在',
                        menu_count=0
                    )
                    db.session.add(batch_record)
                    continue
                
                # 尝试获取菜单数据
                try:
                    session = requests.Session()
                    upload_context = url_update_context(session, root_url, suffix, username, password)
                    menu_data = test.get_menu(upload_context)
                    
                    if menu_data and len(menu_data) > 0:
                        batch_record = BatchUrlFind(
                            user_id=current_user.id,
                            name=name,
                            root_url=root_url,
                            suffix=suffix,
                            username=username,
                            password=password,
                            status='success',
                            error_message=None,
                            menu_count=len(menu_data),
                            menu_data=json.dumps(menu_data, ensure_ascii=False)
                        )
                    else:
                        batch_record = BatchUrlFind(
                            user_id=current_user.id,
                            name=name,
                            root_url=root_url,
                            suffix=suffix,
                            username=username,
                            password=password,
                            status='no_menu',
                            error_message='未获取到菜单数据',
                            menu_count=0
                        )
                    db.session.add(batch_record)
                        
                except Exception as e:
                    batch_record = BatchUrlFind(
                        user_id=current_user.id,
                        name=name,
                        root_url=root_url,
                        suffix=suffix,
                        username=username,
                        password=password,
                        status='error',
                        error_message=f'获取菜单失败: {str(e)}',
                        menu_count=0
                    )
                    db.session.add(batch_record)
                    
            except Exception as e:
                batch_record = BatchUrlFind(
                    user_id=current_user.id,
                    name=f'第{index+1}行',
                    root_url='',
                    suffix='',
                    username='',
                    password='',
                    status='error',
                    error_message=f'处理行数据失败: {str(e)}',
                    menu_count=0
                )
                db.session.add(batch_record)
        
        # 提交所有记录
        db.session.commit()
        
        flash(f'Excel文件处理完成，共处理 {len(df)} 条记录', 'success')
        return redirect(url_for('user.url_management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Excel文件处理失败: {str(e)}', 'error')
        return redirect(url_for('user.url_management'))

@user.route('/confirm_batch_upload', methods=['POST'])
@login_required
def confirm_batch_upload():
    """
    确认批量添加URL上下文
    根据用户选择的结果批量添加到数据库
    """
    try:
        from app.models.url_context import BatchUrlFind
        import json
        
        # 获取用户选择的项目
        selected_indices = request.form.getlist('selected_items')
        
        if not selected_indices:
            flash('请选择要添加的项目', 'error')
            return redirect(url_for('user.url_management'))
        
        # 处理选中的项目
        success_count = 0
        error_count = 0
        
        for index_str in selected_indices:
            try:
                index = int(index_str)
                batch_record = BatchUrlFind.query.filter_by(
                    user_id=current_user.id
                ).offset(index).first()
                
                if batch_record and batch_record.status in ['success', 'no_menu']:
                    # 创建URL上下文
                    url_context = UrlUpdateContext(
                        name=batch_record.name,
                        root_url=batch_record.root_url,
                        suffix=batch_record.suffix,
                        username=batch_record.username,
                        password=batch_record.password
                    )
                    db.session.add(url_context)
                    db.session.flush()  # 获取ID
                    
                    # 添加菜单数据（如果有的话）
                    if batch_record.menu_data:
                        try:
                            menu_data = json.loads(batch_record.menu_data)
                            for menu_item in menu_data:
                                menu_value = menu_item[0]
                                menu_text = menu_item[1]
                                
                                url_menu = UrlMenu(
                                    context_id=url_context.id,
                                    menu_value=menu_value,
                                    menu_text=menu_text
                                )
                                db.session.add(url_menu)
                        except:
                            pass
                    
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                print(f'处理第{index_str}项时出错: {str(e)}')
        
        # 删除所有批量查询记录
        BatchUrlFind.query.filter_by(user_id=current_user.id).delete()
        
        # 提交事务
        db.session.commit()
        
        flash(f'批量添加完成：成功 {success_count} 项，失败 {error_count} 项', 'success')
        return redirect(url_for('user.url_management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'批量添加失败: {str(e)}', 'error')
        return redirect(url_for('user.url_management'))

@user.route('/clear_batch_results', methods=['POST'])
@login_required
def clear_batch_results():
    """
    清除用户的批量查询结果
    """
    try:
        from app.models.url_context import BatchUrlFind
        
        # 删除用户的所有批量查询记录
        deleted_count = BatchUrlFind.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        flash(f'已清除 {deleted_count} 条查询记录', 'success')
        return redirect(url_for('user.url_management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'清除失败: {str(e)}', 'error')
        return redirect(url_for('user.url_management'))

@user.route('/batch_delete_url_contexts', methods=['POST'])
@login_required
def batch_delete_url_contexts():
    """
    批量删除URL上下文
    根据选中的ID列表批量删除URL上下文和关联的菜单数据
    """
    try:
        # 获取选中的ID列表
        selected_ids_str = request.form.get('selected_ids', '')
        if not selected_ids_str:
            flash('请选择要删除的项目', 'error')
            return redirect(url_for('user.url_management'))
        
        # 解析ID列表
        selected_ids = [int(id_str.strip()) for id_str in selected_ids_str.split(',') if id_str.strip()]
        
        if not selected_ids:
            flash('没有有效的选择项', 'error')
            return redirect(url_for('user.url_management'))
        
        # 查找并删除URL上下文
        deleted_count = 0
        for context_id in selected_ids:
            url_context = UrlUpdateContext.query.get(context_id)
            if url_context:
                db.session.delete(url_context)
                deleted_count += 1
        
        db.session.commit()
        
        flash(f'成功删除 {deleted_count} 个URL上下文', 'success')
        return redirect(url_for('user.url_management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'批量删除失败: {str(e)}', 'error')
        return redirect(url_for('user.url_management'))

@user.route('/batch_export_url_contexts', methods=['POST'])
@login_required
def batch_export_url_contexts():
    """
    批量导出URL上下文为Excel文件
    导出格式：name, root_url, suffix, username, password, menus
    """
    try:
        from flask import make_response
        import pandas as pd
        import io
        
        # 获取选中的ID列表
        selected_ids_str = request.form.get('selected_ids', '')
        if not selected_ids_str:
            flash('请选择要导出的项目', 'error')
            return redirect(url_for('user.url_management'))
        
        # 解析ID列表
        selected_ids = [int(id_str.strip()) for id_str in selected_ids_str.split(',') if id_str.strip()]
        
        if not selected_ids:
            flash('没有有效的选择项', 'error')
            return redirect(url_for('user.url_management'))
        
        # 查询选中的URL上下文
        url_contexts = UrlUpdateContext.query.filter(UrlUpdateContext.id.in_(selected_ids)).all()
        
        if not url_contexts:
            flash('没有找到要导出的数据', 'error')
            return redirect(url_for('user.url_management'))
        
        # 准备导出数据
        export_data = []
        for context in url_contexts:
            # 获取菜单数据
            menus = UrlMenu.query.filter_by(context_id=context.id).all()
            menu_texts = [menu.menu_text for menu in menus]
            menus_str = '，'.join(menu_texts) if menu_texts else ''
            
            export_data.append({
                'name': context.name or '',
                'root_url': context.root_url,
                'suffix': context.suffix,
                'username': context.username,
                'password': context.password,
                'menus': menus_str
            })
        
        # 创建DataFrame
        df = pd.DataFrame(export_data)
        
        # 创建Excel文件
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='URL数据', index=False)
        
        output.seek(0)
        
        # 创建响应
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=url_contexts_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        flash(f'成功导出 {len(export_data)} 条数据', 'success')
        return response
        
    except Exception as e:
        flash(f'批量导出失败: {str(e)}', 'error')
        return redirect(url_for('user.url_management'))
