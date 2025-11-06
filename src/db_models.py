"""
数据库模型：通用数据库模型，支持多任务多数据库

新架构特性：
- 支持多个数据库文件（每个任务一个数据库）
- 使用 JSON 字段存储动态业务数据
- 不再依赖 db_config.py
"""

from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()


class Annotation(Base):
    """
    标注记录表（通用版本）
    
    使用 JSON 字段存储所有业务数据，支持不同任务的不同字段
    """
    __tablename__ = 'annotations'
    
    # 主键
    model_id = Column(String(255), primary_key=True, comment='模型ID')
    
    # 元数据字段（所有任务共有）
    annotated = Column(Boolean, default=False, nullable=False, comment='是否已标注')
    uid = Column(String(100), default='', nullable=False, comment='标注者ID')
    score = Column(Integer, default=1, nullable=False, comment='质量分数')
    
    # 业务数据（JSON格式，存储所有字段）
    data = Column(JSON, default={}, comment='业务数据JSON')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    def to_dict(self):
        """
        转换为字典格式
        
        Returns:
            包含元数据和业务数据的完整字典
        """
        result = {
            'annotated': self.annotated,
            'uid': self.uid,
            'score': self.score,
        }
        
        # 合并业务数据
        if self.data:
            result.update(self.data)
        
        return result
    
    def to_jsonl_format(self):
        """转换为 JSONL 格式"""
        return {self.model_id: self.to_dict()}


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment='用户名')
    password_hash = Column(String(255), nullable=False, comment='密码哈希')
    name = Column(String(100), nullable=False, comment='真实姓名')
    role = Column(String(20), default='annotator', comment='角色：admin/annotator')
    created_at = Column(DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'role': self.role
        }


class TaskAssignment(Base):
    """任务分配表"""
    __tablename__ = 'task_assignments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(255), nullable=False, comment='模型ID')
    user_id = Column(Integer, nullable=False, comment='用户ID')
    assigned_at = Column(DateTime, default=datetime.now, comment='分配时间')
    status = Column(String(20), default='pending', comment='状态：pending/in_progress/completed')
    
    def to_dict(self):
        return {
            'id': self.id,
            'model_id': self.model_id,
            'user_id': self.user_id,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'status': self.status
        }


# ========================
# 数据库引擎和会话
# ========================

def get_engine(db_path: str = None):
    """
    获取数据库引擎
    
    Args:
        db_path: 数据库文件路径（如 "databases/annotation.db"）
                如果为None，使用默认路径 "annotations.db"
    
    Returns:
        SQLAlchemy engine对象
    """
    if db_path is None:
        db_path = "annotations.db"
    
    # 确保目录存在
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    # 创建引擎
    db_url = f"sqlite:///{db_path}"
    return create_engine(db_url, echo=False)


def get_session(db_path: str = None):
    """
    获取数据库会话
    
    Args:
        db_path: 数据库文件路径
    
    Returns:
        SQLAlchemy session对象
    """
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()


def init_database(db_path: str = None):
    """
    初始化数据库（创建所有表）
    
    Args:
        db_path: 数据库文件路径
    """
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    print(f"✅ 数据库初始化完成: {db_path or 'annotations.db'}")


if __name__ == "__main__":
    # 测试：创建数据库
    init_database("test.db")

