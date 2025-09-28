"""
[1-2] 文件数据模型
管理用户上传的txt文件信息和执行状态
"""
import os
from datetime import datetime
from app import db

class File(db.Model):
    """
    [1-2.1] 文件模型类
    存储用户上传文件的元信息和执行状态
    """
    __tablename__ = 'files'
    
    # [1-2.1.1] 文件基本信息字段
    id = db.Column(db.Integer, primary_key=True, comment='文件ID主键')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='所属用户ID')
    filename = db.Column(db.String(255), nullable=False, comment='存储文件名')
    original_filename = db.Column(db.String(255), nullable=False, comment='原始文件名')
    file_path = db.Column(db.String(500), nullable=False, comment='文件存储路径')
    file_size = db.Column(db.Integer, nullable=False, comment='文件大小(字节)')
    upload_time = db.Column(db.DateTime, default=datetime.utcnow, comment='文件上传时间')
    
    # [1-2.1.2] 文件执行状态字段
    is_executed = db.Column(db.Boolean, default=False, comment='是否已执行')
    executed_at = db.Column(db.DateTime, comment='执行完成时间')
    
    # [1-2.1.3] 关联关系
    task_executions = db.relationship('TaskExecution', backref='file', lazy='dynamic',
                                    cascade='all, delete-orphan'
                                      )
                                      # , comment='文件执行记录')
    
    def __init__(self, user_id, filename, original_filename, file_path, file_size):
        """
        [1-2.1.4] 文件对象初始化
        """
        self.user_id = user_id
        self.filename = filename
        self.original_filename = original_filename
        self.file_path = file_path
        self.file_size = file_size
    
    def read_content(self):
        """
        [2-2.1] 读取文件内容
        用于任务执行时获取文件内容
        """
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                raise FileNotFoundError(f"文件不存在: {self.file_path}")
        except Exception as e:
            raise Exception(f"读取文件失败: {str(e)}")
    
    # def mark_as_executed(self):
    #     """
    #     [4-2.3] 标记文件为已执行
    #     任务执行完成后调用
    #     """
    #     self.is_executed = True
    #     self.executed_at = datetime.utcnow()
    #     db.session.commit()
    #
    def move_to_executed_folder(self):
        """
        [4-2.4] 移动文件到已执行文件夹
        保持文件系统的组织结构
        """
        try:
            # 构建已执行文件夹路径
            user_upload_dir = os.path.dirname(self.file_path)
            executed_dir = os.path.join(user_upload_dir, 'executed')
            
            # 创建已执行文件夹（如果不存在）
            if not os.path.exists(executed_dir):
                os.makedirs(executed_dir)
            
            # 移动文件
            new_path = os.path.join(executed_dir, self.filename)
            if os.path.exists(self.file_path):
                os.rename(self.file_path, new_path)
                self.file_path = new_path
                db.session.commit()
                return True
            return False
        except Exception as e:
            raise Exception(f"移动文件失败: {str(e)}")
    
    def get_file_info(self):
        """
        [1-2.2] 获取文件详细信息
        返回包含文件状态的字典
        """
        return {
            'id': self.id,
            'filename': self.original_filename,
            'size': self.file_size,
            'upload_time': self.upload_time.strftime('%Y-%m-%d %H:%M:%S'),
            'is_executed': self.is_executed,
            'executed_at': self.executed_at.strftime('%Y-%m-%d %H:%M:%S') if self.executed_at else None
        }
    
    def delete_file(self):
        """
        [1-2.3] 删除文件和记录
        同时删除物理文件和数据库记录
        """
        try:
            # 删除物理文件
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
            
            # 删除数据库记录
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise Exception(f"删除文件失败: {str(e)}")
    
    def __repr__(self):
        """
        [1-2.4] 文件对象字符串表示
        """
        return f'<File {self.original_filename} (User: {self.user_id})>'