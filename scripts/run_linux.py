#!/usr/bin/env python3
"""
[Linux生产环境启动脚本]
使用Gunicorn启动Flask应用和WebSocket服务
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.scheduler import task_scheduler

# 设置生产环境
os.environ.setdefault('FLASK_ENV', 'production')

# 创建应用实例
app, socketio = create_app('production')

# 定义WebSocket事件处理器
@socketio.on("message", namespace="/ws")
def socket(message):
    print(f"接收到消息: {message['data']}")
    for i in range(1, 10):
        socketio.sleep(1)
        socketio.emit("response", {"data": i}, namespace="/ws")

@socketio.on('connect', namespace='/ws')
def test_connect():
    print('客户端已连接到 /ws 命名空间')

@socketio.on('disconnect', namespace='/ws')
def test_disconnect():
    print('客户端已断开连接')

# 测试路由
@app.route('/push')
def push_once():
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

# 启动所有运行中的任务
with app.app_context():
    task_scheduler.start_all_running_tasks()
    app.logger.info("任务调度器已启动，所有运行中的任务已恢复")

if __name__ == '__main__':
    # 这个分支用于直接运行，但在生产环境应该使用 gunicorn 命令启动
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)

