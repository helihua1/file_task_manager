#!/usr/bin/env python3
"""
[应用启动脚本]
启动Flask应用和任务调度器
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.scheduler import task_scheduler

def run_app():
    """
    [启动应用]
    创建Flask应用并启动开发服务器
    """
    # [设置环境变量]
    os.environ.setdefault('FLASK_ENV', 'development')
    
    # [创建应用实例]
    app = create_app()
    
    # [启动所有运行中的任务]
    with app.app_context():
        task_scheduler.start_all_running_tasks()
        app.logger.info("任务调度器已启动，所有运行中的任务已恢复")
    
    # [获取配置]
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"正在启动应用...")
    print(f"访问地址: http://{host}:{port}")
    print(f"调试模式: {'开启' if debug else '关闭'}")
    print(f"管理员账户: admin / admin123")
    
    # [启动Flask应用]
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True,
        use_reloader=False
    )

if __name__ == '__main__':
    run_app()