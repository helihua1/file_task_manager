"""
[认证视图控制器]
处理用户登录、注册、登出等认证相关操作
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from app.models.user import User, db

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    [1-1] 用户登录处理
    GET: 显示登录页面
    POST: 验证用户凭证并登录
    """
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = bool(request.form.get('remember_me'))
        
        # [1-1.1] 验证用户输入
        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('auth/login.html')
        
        # [1-1.2] 查找用户并验证密码
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            # [1-1.3] 登录成功，更新登录时间
            login_user(user, remember=remember_me)
            user.update_last_login()
            
            # [1-1.4] 重定向到目标页面或仪表板
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('admin.dashboard') if user.is_admin else url_for('user.dashboard')
            
            flash(f'欢迎回来，{user.username}!', 'success')
            return redirect(next_page)
        else:
            flash('用户名或密码错误', 'error')
    
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """
    [1-2] 用户注册处理
    GET: 显示注册页面
    POST: 创建新用户账户
    """
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # [1-2.1] 验证用户输入
        if not all([username, email, password, confirm_password]):
            flash('请填写所有必填字段', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('密码长度至少为6位', 'error')
            return render_template('auth/register.html')
        
        # [1-2.2] 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册', 'error')
            return render_template('auth/register.html')
        
        try:
            # [1-2.3] 创建新用户
            user = User(username=username, email=email, password=password)
            db.session.add(user)
            db.session.commit()
            
            flash('注册成功！请登录', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('注册失败，请重试', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    """
    [1-3] 用户登出处理
    清除用户会话并重定向到首页
    """
    username = current_user.username
    logout_user()
    flash(f'再见，{username}!', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    [1-4] 用户个人资料管理
    GET: 显示个人资料页面
    POST: 更新个人资料
    """
    if request.method == 'POST':
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # [1-4.1] 更新邮箱
        if email and email != current_user.email:
            if User.query.filter_by(email=email).first():
                flash('邮箱已被其他用户使用', 'error')
            else:
                current_user.email = email
                db.session.commit()
                flash('邮箱更新成功', 'success')
        
        # [1-4.2] 更新密码
        if current_password and new_password:
            if not current_user.check_password(current_password):
                flash('当前密码错误', 'error')
            elif new_password != confirm_password:
                flash('两次输入的新密码不一致', 'error')
            elif len(new_password) < 6:
                flash('新密码长度至少为6位', 'error')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('密码更新成功', 'success')
    
    return render_template('auth/profile.html', user=current_user)