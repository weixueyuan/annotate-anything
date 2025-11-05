"""
数据缓存管理模块

为数据处理器提供智能缓存层，优化数据加载和更新机制
"""

import time
from typing import Dict, Any, Set, List


class DataCache:
    """
    智能数据缓存管理器
    
    负责数据的缓存、增量更新和按需加载，优化数据库访问性能
    """
    
    def __init__(self, data_handler, ttl: int = 300):
        """
        初始化数据缓存管理器
        
        Args:
            data_handler: 数据处理器（DatabaseHandler或JSONLHandler）
            ttl: 缓存有效期（秒）
        """
        self.data_handler = data_handler
        self.cache = {}  # 缓存所有数据
        self.modified = set()  # 已修改项目的ID集合
        self.visible_keys = []  # 当前用户可见的键列表
        self.last_load_time = None  # 上次完整加载时间
        self.ttl = ttl  # 缓存有效期(秒)
        self.user_uid = None  # 当前用户ID
    
    def set_user(self, user_uid: str):
        """设置当前用户ID"""
        self.user_uid = user_uid
    
    def get_all_data(self, force_reload: bool = False) -> Dict:
        """
        获取所有数据
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            数据字典
        """
        current_time = time.time()
        
        # 检查是否需要重新加载
        cache_expired = (
            self.last_load_time is None or 
            (current_time - self.last_load_time) > self.ttl
        )
        
        if not self.cache or cache_expired or force_reload:
            self.cache = self.data_handler.load_data()
            self.last_load_time = current_time
            self.modified.clear()
        
        return self.cache
    
    def get_item(self, model_id: str, force_reload: bool = False) -> Any:
        """
        获取单条数据
        
        Args:
            model_id: 模型ID
            force_reload: 是否强制重新加载
            
        Returns:
            数据项或None
        """
        # 如果缓存为空，先加载全部
        if not self.cache:
            self.get_all_data()
        
        # 如果要强制重新加载或项目不在缓存中
        if force_reload or model_id not in self.cache:
            # 检查是否实现了单条加载方法
            if hasattr(self.data_handler, 'get_item'):
                item = self.data_handler.get_item(model_id)
                if item:
                    self.cache[model_id] = item
            else:
                # 没有单条加载方法，重新加载全部
                self.get_all_data(force_reload=True)
        
        return self.cache.get(model_id)
    
    def update_visible_keys(self) -> List[str]:
        """
        更新当前用户可见的键列表
        
        Returns:
            可见键列表
        """
        # 确保缓存已加载
        self.get_all_data()
        
        # 重新计算可见键
        self.visible_keys = []
        for key, value in self.cache.items():
            # 解析数据项
            if hasattr(self.data_handler, 'parse_item'):
                item_attrs = self.data_handler.parse_item(value)
                item_uid = item_attrs.get('uid', '')
                # 如果数据未分配或属于当前用户
                if not item_uid or item_uid == self.user_uid:
                    self.visible_keys.append(key)
        
        return self.visible_keys
    
    def get_visible_keys(self, force_update: bool = False) -> List[str]:
        """
        获取当前用户可见的键列表
        
        Args:
            force_update: 是否强制更新
            
        Returns:
            可见键列表
        """
        if not self.visible_keys or force_update:
            self.update_visible_keys()
        
        return self.visible_keys
    
    def assign_to_user(self, model_id: str, user_uid: str) -> bool:
        """
        将数据分配给用户（浏览即占有）
        
        Args:
            model_id: 模型ID
            user_uid: 用户ID
            
        Returns:
            是否成功
        """
        # 先在数据源中分配
        result = self.data_handler.assign_to_user(model_id, user_uid)
        
        if result:
            # 分配成功，更新缓存
            item = self.get_item(model_id, force_reload=True)
            self.modified.add(model_id)
            
            # 如果用户ID是当前用户，更新可见键
            if user_uid == self.user_uid and model_id not in self.visible_keys:
                self.visible_keys.append(model_id)
        
        return result
    
    def update_item(self, model_id: str, data: Dict, **kwargs) -> Dict:
        """
        更新单条数据
        
        Args:
            model_id: 模型ID
            data: 更新数据
            **kwargs: 其他参数
            
        Returns:
            操作结果字典
        """
        # 在数据源中更新
        result = self.data_handler.save_item(model_id, data, **kwargs)
        
        if result["success"]:
            # 更新成功，更新缓存
            self.get_item(model_id, force_reload=True)
            self.modified.add(model_id)
        
        return result
    
    def is_modified(self, model_id: str) -> bool:
        """检查数据项是否被修改过"""
        return model_id in self.modified
    
    def load_batch(self, batch_size: int = 100, page: int = 1) -> Dict:
        """
        分批加载数据
        
        Args:
            batch_size: 批次大小
            page: 页码
            
        Returns:
            批次数据信息
        """
        # 检查是否支持分批加载
        if hasattr(self.data_handler, 'load_data_batch'):
            return self.data_handler.load_data_batch(batch_size, page)
        
        # 不支持分批加载，模拟实现
        all_data = self.get_all_data()
        keys = list(all_data.keys())
        
        # 计算起止索引
        start_idx = (page - 1) * batch_size
        end_idx = min(start_idx + batch_size, len(keys))
        
        # 提取当前批次
        batch_keys = keys[start_idx:end_idx]
        batch_data = {k: all_data[k] for k in batch_keys}
        
        return {
            "data": batch_data,
            "page": page,
            "batch_size": batch_size,
            "total_count": len(all_data),
            "has_more": end_idx < len(keys)
        }
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        return {
            'cache_size': len(self.cache),
            'visible_count': len(self.visible_keys),
            'modified_count': len(self.modified),
            'last_load_time': self.last_load_time,
            'ttl': self.ttl
        }
    
    def clear(self):
        """清除缓存"""
        self.cache = {}
        self.modified.clear()
        self.visible_keys = []
        self.last_load_time = None