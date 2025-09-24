#!/usr/bin/env python3
"""
[数据库初始化脚本]
创建数据库表结构和初始数据
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.user import User

def init_database():
    """
    [初始化数据库]
    创建所有表结构并插入初始数据
    """
    """
    当调用 db.create_all() 时，SQLAlchemy 会：
    扫描所有继承自 db.Model 的类
    读取每个类的 __tablename__ 属性
    根据模型类中定义的字段结构创建对应的数据表
    使用 __tablename__ 中指定的名字作为实际的数据库表名
    所以，如果你想修改数据表的名字，只需要修改对应模型类中的 __tablename__ 属性即可。
    """
    """
    1. User.query
    User 是模型类（继承自 db.Model）
    .query 是 SQLAlchemy 提供的查询接口
    相当于 SQL 中的 SELECT * FROM users
    2. .filter_by(username='admin')
    .filter_by() 是过滤方法
    username='admin' 是过滤条件
    相当于 SQL 中的 WHERE username = 'admin'
    3. .first()
    获取查询结果的第一条记录
    如果没有找到记录，返回 None
    相当于 SQL 中的 LIMIT 1

    等于：
    SELECT * FROM users WHERE username = 'admin' LIMIT 1;
    """
    """
    3. Session 跟踪机制
    SQLAlchemy 的 session 会：
    跟踪所有添加到 session 的对象
    记录每个对象的类型和状态变化
    在 commit() 时，根据对象的类型确定对应的表
    4. 实际执行过程
    当调用 db.session.commit() 时：
    扫描 session 中的所有对象
    根据对象的类名找到对应的 __tablename__
    生成相应的 SQL 语句：
    User 对象 → INSERT INTO users (...)
    File 对象 → INSERT INTO files (...)
    """
    app = create_app()
    
    with app.app_context(): # 进入应用上下文
        print('正在创建数据库表...')
        
        # [删除所有表（谨慎使用）]
        # db.drop_all()
        
        # [创建所有表]

        db.create_all()
        print('数据库表创建完成')
        
        
        # [检查是否已有管理员用户]
        admin_user = User.query.filter_by(username='admin').first()
        
        if not admin_user:
            # [创建默认管理员]
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            admin_user.is_admin = True
            db.session.add(admin_user)
            
            # [创建测试用户]
            test_user = User(
                username='testuser',
                email='test@example.com',
                password='test123'
            )
            db.session.add(test_user)

            db.session.commit()
            
            print('默认用户创建完成:')
            print('  管理员: admin / admin123')
            print('  测试用户: testuser / test123')
        else:
            print('数据库已初始化，跳过用户创建')
        
        print('数据库初始化完成！')

if __name__ == '__main__':
    init_database()