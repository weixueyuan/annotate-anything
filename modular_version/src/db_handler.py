"""
数据库处理器：简化版
"""

import json
from typing import Dict, Any, Optional
from sqlalchemy.exc import IntegrityError
from .db_models import Annotation, get_session, init_database
from .field_processor import FieldProcessor


class DatabaseHandler:
    """数据库处理类"""
    
    def __init__(self, db_path: str = 'databases/annotation.db'):
        """
        初始化数据库处理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.field_processor = FieldProcessor()
        # 初始化数据库
        init_database(db_path)
        self.session = get_session(db_path)
    
    def load_data(self) -> Dict[str, Annotation]:
        """加载所有数据"""
        try:
            annotations = self.session.query(Annotation).all()
            return {ann.model_id: ann for ann in annotations}
        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return {}
            
    def get_item(self, model_id: str) -> Optional[Annotation]:
        """
        加载单条数据
        
        Args:
            model_id: 模型ID
            
        Returns:
            Annotation对象或None
        """
        try:
            annotation = self.session.query(Annotation).filter_by(model_id=model_id).first()
            return annotation
        except Exception as e:
            print(f"❌ 加载数据项失败: {model_id} - {e}")
            return None
            
    def load_data_batch(self, batch_size: int = 100, page: int = 1) -> Dict:
        """
        分批加载数据
        
        Args:
            batch_size: 每批数据量
            page: 页码（从1开始）
            
        Returns:
            批次数据信息字典
        """
        try:
            # 计算偏移量
            offset = (page - 1) * batch_size
            
            # 查询当前批次数据
            annotations = self.session.query(Annotation) \
                              .order_by(Annotation.model_id) \
                              .offset(offset) \
                              .limit(batch_size) \
                              .all()
            
            # 构建数据字典
            batch_data = {ann.model_id: ann for ann in annotations}
            
            # 获取总数（仅在第一页时查询，避免重复计算）
            total_count = None
            if page == 1:
                total_count = self.session.query(Annotation).count()
            
            return {
                "data": batch_data,
                "page": page,
                "batch_size": batch_size,
                "total_count": total_count,
                "has_more": len(annotations) == batch_size
            }
        except Exception as e:
            print(f"❌ 批量加载数据失败: 页码={page}, 批次大小={batch_size} - {e}")
            return {
                "data": {},
                "page": page,
                "batch_size": batch_size,
                "total_count": 0,
                "has_more": False,
                "error": str(e)
            }
            
    def load_visible_items(self, user_uid: str) -> Dict[str, Annotation]:
        """
        只加载当前用户可见的项目
        
        Args:
            user_uid: 用户ID
            
        Returns:
            可见数据字典
        """
        try:
            # 使用SQL筛选条件: uid为空 或 uid等于当前用户
            items = self.session.query(Annotation) \
                       .filter((Annotation.uid == user_uid) |
                               (Annotation.uid == '') |
                               (Annotation.uid.is_(None))) \
                       .all()
            
            return {item.model_id: item for item in items}
        except Exception as e:
            print(f"❌ 加载用户可见数据失败: {user_uid} - {e}")
            return {}
    
    def parse_item(self, item: Annotation) -> Dict:
        """解析单条数据"""
        if isinstance(item, Annotation):
            result = item.to_dict()
            
            # 预处理 placement：数组转字符串（兼容旧版逻辑）
            if 'placement' in result and isinstance(result['placement'], list):
                result['placement'] = ', '.join(result['placement'])
            
            return result
        return {}
        
    def get_item_attrs(self, model_id: str) -> Dict:
        """
        获取单条数据的属性字典
        
        Args:
            model_id: 模型ID
            
        Returns:
            属性字典
        """
        item = self.get_item(model_id)
        if item:
            return self.parse_item(item)
        return {}
    
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
            # 使用数据库锁确保原子操作
            annotation = self.session.query(Annotation).filter_by(model_id=model_id).with_for_update().first()
            if not annotation:
                return False
                
            # 检查是否已被其他用户占有
            current_uid = annotation.uid
            if current_uid and current_uid != uid and current_uid != '':
                # 已被其他用户占有，不允许覆盖
                self.session.rollback()  # 释放锁
                print(f"⚠️ 数据已被用户 '{current_uid}' 占有，无法分配给 '{uid}'")
                return False
            
            # 未被占有或被当前用户占有，可以更新
            annotation.uid = uid
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            print(f"❌ 分配失败: {e}")
            return False
    
    def save_item(self, model_id: str, data: Dict, score: int = 1, uid: str = None):
        """
        保存标注数据（实际标注保存）
        
        Args:
            model_id: 模型ID
            data: 业务数据字典
            score: 标注得分（0=有错误, 1=完成）
            uid: 用户ID
            
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
            annotation = self.session.query(Annotation).filter_by(model_id=model_id).first()
            
            if not annotation:
                # 记录不存在
                return {
                    "success": False,
                    "error": "NOT_FOUND",
                    "message": f"未找到ID为 {model_id} 的记录"
                }
                
            # 更新标注状态和数据
            annotation.annotated = True  # 保存即标记为已标注
            annotation.uid = uid if uid else annotation.uid
            annotation.score = score
            # 更新业务数据（排除元数据字段）
            annotation.data = {k: v for k, v in data.items() if k not in ['uid', 'annotated', 'score']}
            
            self.session.commit()
            return {
                "success": True,
                "message": f"成功保存记录 {model_id}",
                "model_id": model_id
            }
            
        except IntegrityError as e:
            self.session.rollback()
            error_message = str(e)
            print(f"❌ 保存失败(数据完整性错误): {error_message}")
            return {
                "success": False,
                "error": "INTEGRITY_ERROR",
                "message": "数据冲突，请检查输入"
            }
            
        except Exception as e:
            self.session.rollback()
            error_message = str(e)
            print(f"❌ 保存失败: {error_message}")
            return {
                "success": False,
                "error": "UNKNOWN_ERROR",
                "message": error_message
            }
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        try:
            total = self.session.query(Annotation).count()
            annotated = self.session.query(Annotation).filter_by(annotated=True).count()
            return {
                'total': total,
                'annotated': annotated,
                'pending': total - annotated
            }
        except Exception as e:
            print(f"❌ 获取统计失败: {e}")
            return {'total': 0, 'annotated': 0, 'pending': 0}
    
    def export_to_jsonl(self, output_dir: str = "exports", filter_by_user=None, only_annotated=False) -> str:
        """
        导出数据库数据为JSONL文件
        
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
            # 构建查询
            query = self.session.query(Annotation)
            
            # 应用过滤条件
            if filter_by_user:
                query = query.filter_by(uid=filter_by_user)
            
            if only_annotated:
                query = query.filter_by(annotated=True)
            
            annotations = query.all()
            
            # 写入JSONL文件
            with open(filepath, 'w', encoding='utf-8') as f:
                for ann in annotations:
                    # 构建完整数据（包含元数据）
                    full_data = {
                        'annotated': ann.annotated,
                        'uid': ann.uid,
                        'score': ann.score,
                    }
                    
                    # 合并业务数据
                    if ann.data:
                        full_data.update(ann.data)
                    
                    # 处理 placement：如果是字符串，转换为数组（JSONL格式）
                    if 'placement' in full_data:
                        if isinstance(full_data['placement'], str):
                            # 字符串转数组
                            full_data['placement'] = [x.strip() for x in full_data['placement'].split(',') if x.strip()]
                        elif isinstance(full_data['placement'], list):
                            # 已经是数组，保持不变
                            pass
                    
                    # 写入 JSONL 格式：{"model_id": {数据}}
                    line_obj = {ann.model_id: full_data}
                    f.write(json.dumps(line_obj, ensure_ascii=False) + '\n')
            
            print(f"✅ 导出完成: {filepath}")
            print(f"   共导出 {len(annotations)} 条记录")
            return filepath
            
        except PermissionError as e:
            error_msg = f"写入文件 '{filepath}' 权限被拒绝"
            print(f"❌ {error_msg}")
            raise PermissionError(error_msg) from e
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 导出失败: {error_msg}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'session'):
            self.session.close()
