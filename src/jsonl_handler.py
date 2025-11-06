"""
JSONL 数据处理器：直接读写 JSONL 文件（用于调试）

提供和 DatabaseHandler 相同的接口
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict


class JSONLItem:
    """JSONL 数据项（模拟 Annotation 对象）"""
    
    def __init__(self, model_id: str, data: dict):
        self.model_id = model_id
        self.annotated = data.get('annotated', False)
        self.uid = data.get('uid', '')
        self.score = data.get('score', 1)
        
        # 业务数据（排除元数据）
        self.data = {k: v for k, v in data.items() 
                     if k not in ['annotated', 'uid', 'score']}
    
    def to_dict(self):
        """转换为字典"""
        result = {
            'annotated': self.annotated,
            'uid': self.uid,
            'score': self.score,
        }
        result.update(self.data)
        return result


class JSONLHandler:
    """JSONL 文件处理类（提供和 DatabaseHandler 相同的接口）"""
    
    def __init__(self, jsonl_path: str):
        """
        初始化 JSONL 处理器
        
        Args:
            jsonl_path: JSONL 文件路径
        """
        self.jsonl_path = jsonl_path
        self._data_cache = None  # 数据缓存
        
        # 初始化字段处理器
        from .field_processor import FieldProcessor
        self.field_processor = FieldProcessor()
        
        # 已知的字段配置（用于处理特殊字段）
        self.field_configs = {
            'placement': {'key': 'placement', 'process': 'array_to_string'},
            # 可以添加其他需要特殊处理的字段
        }
    
    def load_data(self) -> Dict[str, JSONLItem]:
        """加载所有数据（和 DatabaseHandler.load_data 接口一致）"""
        if self._data_cache is not None:
            return self._data_cache
        
        data_dict = {}
        
        if not os.path.exists(self.jsonl_path):
            print(f"⚠️  文件不存在: {self.jsonl_path}")
            return data_dict
        
        try:
            with open(self.jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 解析：{"model_id": {属性字典}}
                    item = json.loads(line)
                    
                    for model_id, attrs in item.items():
                        data_dict[model_id] = JSONLItem(model_id, attrs)
            
            self._data_cache = data_dict
            return data_dict
            
        except Exception as e:
            print(f"❌ 加载 JSONL 失败: {e}")
            return {}
            
    def get_item(self, model_id: str):
        """
        获取单条数据
        
        Args:
            model_id: 模型ID
            
        Returns:
            JSONLItem对象或None
        """
        # 如果缓存未加载，先加载
        if self._data_cache is None:
            self.load_data()
            
        # 从缓存中获取
        return self._data_cache.get(model_id)
    
    def load_data_batch(self, batch_size: int = 100, page: int = 1) -> Dict:
        """
        分批加载数据（模拟实现，JSONL实际是一次性加载）
        
        Args:
            batch_size: 每批数据量
            page: 页码（从1开始）
            
        Returns:
            批次数据信息字典
        """
        # 确保数据已加载
        all_data = self.load_data()
        
        # 获取所有键并排序
        keys = sorted(all_data.keys())
        
        # 计算偏移量和范围
        offset = (page - 1) * batch_size
        end_idx = min(offset + batch_size, len(keys))
        
        # 提取当前批次
        batch_keys = keys[offset:end_idx] if offset < len(keys) else []
        batch_data = {k: all_data[k] for k in batch_keys}
        
        return {
            "data": batch_data,
            "page": page,
            "batch_size": batch_size,
            "total_count": len(all_data),
            "has_more": end_idx < len(keys)
        }
    
    def parse_item(self, item: JSONLItem) -> Dict:
        """解析单条数据（和 DatabaseHandler.parse_item 接口一致）"""
        if isinstance(item, JSONLItem):
            result = item.to_dict()
            
            return result
        return {}
    
    def save_item(self, model_id: str, data: Dict, score: int = 1, uid: str = None):
        """
        保存单条数据（和 DatabaseHandler.save_item 接口一致）
        
        会更新缓存并写回文件
        
        Returns:
            Dict: 包含保存结果的字典，格式为:
                {
                    "success": True/False,
                    "message": "结果描述信息",
                    "error": "错误类型"(可选),
                    "model_id": "已保存的模型ID"(成功时)
                }
        """
        try:
            # 更新缓存
            if self._data_cache is None:
                self._data_cache = self.load_data()
            
            if model_id not in self._data_cache:
                return {
                    "success": False,
                    "error": "NOT_FOUND",
                    "message": f"未找到ID为 {model_id} 的记录"
                }
                
            item = self._data_cache[model_id]
            item.annotated = True
            item.uid = uid if uid else data.get('uid', item.uid)
            item.score = score
            # 更新业务数据（合并而不是覆盖）
            if item.data is None:
                item.data = {}
            
            # 从表单提交的数据中排除元数据字段
            update_data = {k: v for k, v in data.items() if k not in ['uid', 'annotated', 'score']}
            
            # 合并新旧数据
            item.data.update(update_data)
            
            # 写回文件
            self._save_to_file()
            
            # 清除缓存，确保下次读取时从文件加载最新数据（用于修改检测）
            self._data_cache = None
            
            return {
                "success": True,
                "message": f"成功保存记录 {model_id}",
                "model_id": model_id
            }
            
        except PermissionError as e:
            error_message = str(e)
            print(f"❌ 保存失败(权限错误): {error_message}")
            return {
                "success": False,
                "error": "PERMISSION_ERROR",
                "message": "保存文件权限被拒绝"
            }
            
        except Exception as e:
            error_message = str(e)
            print(f"❌ 保存失败: {error_message}")
            return {
                "success": False,
                "error": "UNKNOWN_ERROR",
                "message": error_message
            }
    
    def _save_to_file(self):
        """将缓存写回 JSONL 文件"""
        # 备份原文件
        if os.path.exists(self.jsonl_path):
            backup_dir = os.path.join(os.path.dirname(self.jsonl_path), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"backup_{ts}.jsonl")
            shutil.copy2(self.jsonl_path, backup_file)
        
        # 写入新数据
        with open(self.jsonl_path, 'w', encoding='utf-8') as f:
            for model_id, item in self._data_cache.items():
                # 构建完整数据（包含元数据）
                full_data = {
                    'annotated': item.annotated,
                    'uid': item.uid,
                    'score': item.score,
                }
                full_data.update(item.data)
                
                # 写入 JSONL 格式
                line_obj = {model_id: full_data}
                f.write(json.dumps(line_obj, ensure_ascii=False) + '\n')
        
        print(f"💾 已保存到: {self.jsonl_path}")
    
    def get_statistics(self) -> Dict:
        """获取统计信息（和 DatabaseHandler.get_statistics 接口一致）"""
        if self._data_cache is None:
            self._data_cache = self.load_data()
        
        total = len(self._data_cache)
        annotated = sum(1 for item in self._data_cache.values() if item.annotated)
        
        return {
            'total': total,
            'annotated': annotated,
            'pending': total - annotated
        }
    
    def close(self):
        """关闭（占位方法，保持接口一致）"""
        pass
        
    def assign_to_user(self, model_id: str, uid: str):
        """
        仅分配数据给用户（浏览即占有）
        
        只更新 uid 字段，不触碰其他任何数据
        
        Args:
            model_id: 模型ID
            uid: 用户ID
            
        Returns:
            bool: 是否成功分配
        """
        try:
            # 确保缓存已加载
            if self._data_cache is None:
                self._data_cache = self.load_data()
                
            # 检查记录是否存在
            if model_id not in self._data_cache:
                print(f"⚠️ 分配失败: 未找到ID为 {model_id} 的记录")
                return False
                
            # 获取当前项
            item = self._data_cache[model_id]
            
            # 检查是否已被其他用户占有
            current_uid = item.uid
            if current_uid and current_uid != uid and current_uid != '':
                # 已被其他用户占有，不允许覆盖
                print(f"⚠️ 数据已被用户 '{current_uid}' 占有，无法分配给 '{uid}'")
                return False
            
            # 未被占有或被当前用户占有，可以更新
            item.uid = uid
            
            # 写回文件
            self._save_to_file()
            
            # 清除缓存
            self._data_cache = None
            
            return True
            
        except Exception as e:
            print(f"❌ 分配失败: {e}")
            return False
            
    def export_to_jsonl(self, output_dir: str = "exports", filter_by_user=None, only_annotated=False):
        """
        导出数据为JSONL文件
        
        Args:
            output_dir: 输出目录，默认为 "exports"
            filter_by_user: 可选，按用户筛选
            only_annotated: 是否只导出已标注的数据
            
        Returns:
            导出文件的路径
        """
        import os
        from datetime import datetime
        
        # 创建导出目录
        try:
            os.makedirs(output_dir, exist_ok=True)
        except PermissionError as e:
            error_msg = f"无法创建目录 '{output_dir}': 权限被拒绝"
            print(f"❌ {error_msg}")
            raise PermissionError(error_msg) from e
        except OSError as e:
            error_msg = f"无法创建目录 '{output_dir}': {str(e)}"
            print(f"❌ {error_msg}")
            raise OSError(error_msg) from e
        
        # 生成文件名（带日期时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.jsonl"
        filepath = os.path.join(output_dir, filename)
        
        try:
            # 确保缓存已加载
            if self._data_cache is None:
                self._data_cache = self.load_data()
                
            # 筛选数据
            filtered_items = []
            for model_id, item in self._data_cache.items():
                # 应用过滤条件
                if filter_by_user and item.uid != filter_by_user:
                    continue
                
                if only_annotated and not item.annotated:
                    continue
                    
                filtered_items.append((model_id, item))
            
            # 写入JSONL文件
            with open(filepath, 'w', encoding='utf-8') as f:
                for model_id, item in filtered_items:
                    # 构建完整数据（包含元数据）
                    full_data = item.to_dict()
                    
                    # 处理特殊字段
                    for key, value in list(full_data.items()):
                        if key in self.field_configs:
                            field_config = self.field_configs[key]
                            if isinstance(value, str) and field_config.get('process') == 'array_to_string':
                                full_data[key] = self.field_processor.process_save(field_config, value)
                    
                    # 写入 JSONL 格式：{"model_id": {数据}}
                    line_obj = {model_id: full_data}
                    f.write(json.dumps(line_obj, ensure_ascii=False) + '\n')
            
            print(f"✅ 导出完成: {filepath}")
            print(f"   共导出 {len(filtered_items)} 条记录")
            return filepath
            
        except PermissionError as e:
            error_msg = f"写入文件 '{filepath}' 权限被拒绝"
            print(f"❌ {error_msg}")
            raise PermissionError(error_msg) from e
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 导出失败: {error_msg}")
            raise

