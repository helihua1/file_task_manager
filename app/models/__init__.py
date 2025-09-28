"""
[1] 数据模型初始化模块
用于导入所有数据模型类，便于统一管理
"""
from .user import User
from .file import File
from .task import Task
from .task_execution import TaskExecution
from .url_context import UrlUpdateContext, UrlMenu, url_update_context

__all__ = ['User', 'File', 'Task', 'TaskExecution', 'UrlUpdateContext', 'UrlMenu', 'url_update_context']
