#!/usr/bin/env python
"""
日志记录模块

将所有终端输出（stdout 和 stderr）同步记录到日志文件中
"""

import sys
from datetime import datetime
from pathlib import Path


class TeeLogger:
    """同时输出到终端和文件的日志记录器"""
    
    def __init__(self, log_file_path):
        """
        初始化日志记录器
        
        Args:
            log_file_path: 日志文件路径
        """
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 打开日志文件（追加模式）
        self.log_file = open(self.log_file_path, 'a', encoding='utf-8')
        
        # 保存原始的 stdout 和 stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # 创建 Tee 对象
        self.stdout_tee = Tee(self.original_stdout, self.log_file)
        self.stderr_tee = Tee(self.original_stderr, self.log_file)
        
        # 记录日志开始时间
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_file.write(f"\n{'='*80}\n")
        self.log_file.write(f"日志开始时间: {start_time}\n")
        self.log_file.write(f"日志文件: {self.log_file_path}\n")
        self.log_file.write(f"{'='*80}\n\n")
        self.log_file.flush()
    
    def start(self):
        """开始记录日志（重定向 stdout 和 stderr）"""
        sys.stdout = self.stdout_tee
        sys.stderr = self.stderr_tee
    
    def stop(self):
        """停止记录日志（恢复原始的 stdout 和 stderr）"""
        # 记录日志结束时间
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_file.write(f"\n{'='*80}\n")
        self.log_file.write(f"日志结束时间: {end_time}\n")
        self.log_file.write(f"{'='*80}\n\n")
        
        # 恢复原始的 stdout 和 stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # 关闭日志文件
        self.log_file.close()
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()


class Tee:
    """同时写入多个文件对象的类"""
    
    def __init__(self, *files):
        """
        初始化 Tee 对象
        
        Args:
            *files: 要写入的文件对象列表
        """
        self.files = files
        # 保存第一个文件对象作为主要参考（通常是原始的 stdout/stderr）
        self.primary_file = files[0] if files else None
    
    def write(self, text):
        """写入文本到所有文件对象"""
        for f in self.files:
            f.write(text)
            # 立即刷新，确保实时写入
            if hasattr(f, 'flush'):
                f.flush()
    
    def flush(self):
        """刷新所有文件对象"""
        for f in self.files:
            if hasattr(f, 'flush'):
                f.flush()
    
    def isatty(self):
        """检查主要文件是否是终端"""
        if self.primary_file and hasattr(self.primary_file, 'isatty'):
            return self.primary_file.isatty()
        return False
    
    def fileno(self):
        """返回主要文件的文件描述符"""
        if self.primary_file and hasattr(self.primary_file, 'fileno'):
            return self.primary_file.fileno()
        raise AttributeError("Tee object has no file descriptor")
    
    def __getattr__(self, name):
        """
        代理其他属性到主要文件对象
        这确保了 Tee 对象可以像原始文件对象一样使用
        """
        if self.primary_file and hasattr(self.primary_file, name):
            return getattr(self.primary_file, name)
        raise AttributeError(f"Tee object has no attribute '{name}'")


def setup_logging(task_name, project_root=None):
    """
    设置日志记录
    
    Args:
        task_name: 任务名称
        project_root: 项目根目录（如果为 None，则自动检测）
    
    Returns:
        TeeLogger 对象
    """
    if project_root is None:
        # 自动检测项目根目录（main_multi.py 的父目录的父目录）
        project_root = Path(__file__).parent.parent
    else:
        project_root = Path(project_root)
    
    # 创建 logs 目录
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成日志文件名：{task_name}_{timestamp}.log
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"{task_name}_{timestamp}.log"
    log_file_path = logs_dir / log_filename
    
    # 创建并返回日志记录器
    logger = TeeLogger(log_file_path)
    
    return logger

