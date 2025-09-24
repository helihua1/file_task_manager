# 文件任务管理系统

## 项目结构
```
file_task_manager/
├── app/                    # 应用主目录
│   ├── __init__.py        # Flask应用工厂
│   ├── models/            # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py        # 用户模型
│   │   ├── task.py        # 任务模型
│   │   └── file.py        # 文件模型
│   ├── views/             # 视图控制器
│   │   ├── __init__.py
│   │   ├── auth.py        # 认证相关路由
│   │   ├── user.py        # 用户功能路由
│   │   ├── admin.py       # 管理员路由
│   │   └── api.py         # API接口
│   ├── templates/         # HTML模板
│   │   ├── base.html      # 基础模板
│   │   ├── auth/          # 认证相关页面
│   │   ├── user/          # 用户界面
│   │   └── admin/         # 管理员界面
│   ├── static/            # 静态资源
│   │   ├── css/
│   │   ├── js/
│   │   └── uploads/       # 用户上传文件存储
│   ├── utils.py           # 工具函数
│   └── scheduler.py       # 任务调度器
├── config/                # 配置文件
│   ├── __init__.py
│   ├── development.py     # 开发环境配置
│   └── production.py      # 生产环境配置
├── scripts/               # 脚本文件
│   ├── init_db.py        # 数据库初始化
│   └── run.py            # 启动脚本
├── logs/                  # 日志文件
├── docs/                  # 文档
├── requirements.txt       # 依赖包
└── README.md             # 项目说明
```

## 执行流程编号说明
1. 用户认证流程
2. 文件上传流程  
3. 任务创建流程
4. 任务执行流程
5. 管理员监控流程