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
    app, socketio = create_app()


    # [定义WebSocket事件处理器] - 必须在socketio.run()之前
    @socketio.on("message", namespace="/ws")
    def socket(message):
        print(f"接收到消息: {message['data']}")
        for i in range(1, 10):
            socketio.sleep(1)
            socketio.emit("response",           # 绑定通信
                        {"data": i},           # 返回socket数据
                      namespace="/ws")
    
    @socketio.on('connect', namespace='/ws')
    def test_connect():
        print('客户端已连接到 /ws 命名空间')
        # socketio.emit('response', {'data':'websocket连接成功,可以看到正在执行的信息'}, namespace='/ws')
    
    @socketio.on('disconnect', namespace='/ws')
    def test_disconnect():
        print('客户端已断开连接')

    # 测试方法
    @app.route('/push')
    def push_once():
        event_name = 'response'
        socketio.emit('task_progress', {
            'task_id': 1,
            'user_id': 2,
            'target_url': 3,
            'file_name': 4,
            'executed_count': 5,
            'total_count': 6,
            'menu_text': 7,
            'timestamp': 8
        }, namespace='/ws')
        return 'done!'


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
    socketio.run(
        app,
        allow_unsafe_werkzeug=True,
        host=host,
        port=port,
        debug=debug,
        use_reloader=False
        # thread=True
    )
        

if __name__ == '__main__':
    run_app()