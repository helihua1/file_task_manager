# 文件任务管理系统 - 安装和使用指南

## 系统简介

文件任务管理系统是一个基于Flask的Web应用，用于管理文件上传和定时任务执行。用户可以上传TXT文件，创建定时任务将文件内容自动发送到指定的目标网站。

## 功能特性

### 用户功能
- 用户注册和登录
- 批量上传TXT文件
- 创建和管理定时任务
- 查看任务执行历史
- 实时监控任务状态

### 管理员功能
- 系统整体监控
- 用户管理
- 任务控制（启动/暂停/停止）
- 系统状态查看

## 安装要求

### 系统要求
- Python 3.8+
- MySQL 8.0+
- 4GB+ RAM
- 10GB+ 磁盘空间

### Python依赖
```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-WTF==1.1.1
WTForms==3.0.1
PyMySQL==1.1.0
APScheduler==3.10.4
Flask-SocketIO==5.3.6
python-socketio==5.8.0
Werkzeug==2.3.7
python-dotenv==1.0.0
requests==2.31.0
cryptography==41.0.4
```

## 安装步骤

### 1. 下载项目
```bash
git clone <repository_url>
cd file_task_manager
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\\Scripts\\activate  # Windows
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置数据库
创建MySQL数据库：
```sql
CREATE DATABASE file_task_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ftm_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON file_task_manager.* TO 'ftm_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. 配置环境变量
复制并编辑配置文件：
```bash
cp .env.example .env
```

编辑`.env`文件：
```
FLASK_ENV=development
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
SECRET_KEY=your-secret-key-here

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=ftm_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=file_task_manager

SCHEDULER_TIMEZONE=Asia/Shanghai
```

### 6. 初始化数据库
```bash
python scripts/init_db.py
```

### 7. 启动应用
```bash
python scripts/run.py
```

## 使用指南

### 首次使用

1. **访问系统**
   - 打开浏览器访问 `http://127.0.0.1:5000`
   - 使用默认管理员账户登录：`admin` / `admin123`

2. **创建普通用户**
   - 点击"立即注册"创建新用户账户
   - 或管理员在用户管理页面创建

### 用户操作流程

#### 1. 上传文件
1. 登录后进入"上传文件"页面
2. 选择一个或多个TXT文件
3. 点击"上传文件"完成上传
4. 在"文件列表"中查看上传的文件

#### 2. 创建任务
1. 进入"创建任务"页面
2. 填写任务配置：
   - **任务名称**: 便于识别的任务名
   - **目标URL**: 文件内容将发送到的网址
   - **执行方法**: 选择A方法（默认）
   - **执行间隔**: 设置任务执行的时间间隔（秒）
   - **开始时间**: 任务开始执行的时间
   - **结束时间**: 任务结束时间（可选）
3. 点击"创建任务"保存配置

#### 3. 管理任务
1. 在"任务管理"页面查看所有任务
2. 点击任务名称查看详细信息
3. 在任务详情页面可以：
   - 启动任务
   - 暂停任务
   - 查看执行历史

#### 4. 监控执行情况
1. 在仪表板查看任务概览
2. 在任务详情页面查看实时进度
3. 查看执行成功/失败的记录

### 管理员操作

#### 1. 系统监控
- 在管理面板查看系统整体状态
- 监控所有用户的任务执行情况
- 查看调度器运行状态

#### 2. 用户管理
- 查看所有用户列表
- 查看用户详细信息和统计数据
- 监控用户活动

#### 3. 任务控制
- 查看所有任务状态
- 启动/暂停/停止任何用户的任务
- 查看任务执行统计

## 配置说明

### 文件上传配置
- 支持的文件类型：`.txt`
- 最大文件大小：100MB
- 存储路径：`app/static/uploads/用户ID/`

### 任务执行配置
- 最小执行间隔：1秒
- 默认执行方法：A方法（HTTP POST）
- 超时时间：30秒
- 最大重试次数：3次

### 系统安全配置
- 密码最小长度：6位
- 会话超时：24小时
- 文件名安全化处理
- SQL注入防护

## 常见问题

### Q: 任务创建后不执行怎么办？
A: 检查以下几点：
1. 任务状态是否为"运行中"
2. 开始时间是否已到
3. 是否有待执行的文件
4. 调度器是否正常运行

### Q: 文件上传失败怎么办？
A: 可能的原因：
1. 文件格式不是TXT
2. 文件大小超过100MB
3. 磁盘空间不足
4. 目录权限问题

### Q: 如何修改管理员密码？
A: 
1. 使用管理员账户登录
2. 进入"个人资料"页面
3. 修改密码并保存

### Q: 如何备份数据？
A: 
1. 备份MySQL数据库
2. 备份上传的文件目录
3. 备份配置文件

## 故障排除

### 数据库连接错误
```bash
# 检查MySQL服务状态
systemctl status mysql

# 测试数据库连接
mysql -h localhost -u ftm_user -p file_task_manager
```

### 调度器不工作
1. 检查应用日志中的错误信息
2. 确认任务状态为"运行中"
3. 重启应用

### 性能问题
1. 检查数据库查询性能
2. 清理长时间未用的文件
3. 调整任务执行间隔
4. 监控系统资源使用

## 系统维护

### 定期维护任务
1. **每日**: 检查系统运行状态
2. **每周**: 清理执行完成的旧文件
3. **每月**: 备份数据库和文件
4. **每季度**: 更新系统依赖包

### 日志管理
- 应用日志位置：`logs/app.log`
- 日志轮转：每10MB创建新文件，保留10个历史文件
- 日志级别：INFO（生产环境）、DEBUG（开发环境）

### 监控指标
- 系统CPU和内存使用率
- 数据库连接数
- 任务执行成功率
- 文件存储空间使用情况

## 技术支持

如遇到技术问题，请提供以下信息：
1. 错误信息截图
2. 系统日志相关部分
3. 操作步骤描述
4. 系统环境信息

联系方式：
- 邮箱：support@example.com
- 文档：查看`docs/`目录下的详细文档