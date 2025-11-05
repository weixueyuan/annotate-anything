#!/usr/bin/env python
"""
物体属性标注导入器（简化版）

⚠️  已过时 - 建议使用通用导入器
推荐使用: python -m importers.generic_importer --task annotation

使用方式：
    python -m importers.annotation_importer                    # 导入默认文件
    python -m importers.annotation_importer --source data.jsonl  # 导入指定文件
    python -m importers.annotation_importer --clean            # 清空后导入
"""

import json
import os
import sys
import argparse
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.db_models import Annotation, get_session, get_engine, Base


class AnnotationImporter:
    """物体属性标注导入器"""
    
    # GIF 基础路径
    BASE_PATH = "/mnt/data/GRScenes-100/instances/renderings"
    
    def __init__(self):
        self.stats = {'imported': 0, 'updated': 0, 'errors': 0}
    
    def build_gif_path(self, model_id: str) -> str:
        """
        根据 model_id 构建 GIF 路径
        
        格式: type-subtype-category-id
        例如: home-others-mirror-31854b50393738c38b46962840048a04
        """
        parts = model_id.split('-')
        if len(parts) >= 4:
            type_folder = f"{parts[0]}_objects"
            subtype_folder = parts[1]
            category_folder = parts[2]
            model_id_part = parts[3]
            
            gif_path = os.path.join(
                self.BASE_PATH, type_folder, subtype_folder, category_folder,
                "thumbnails/merged_views", model_id_part, f"{model_id_part}_fixed.gif"
            )
            return gif_path
        return ""
    
    def parse_jsonl(self, filepath: str):
        """解析JSONL文件"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        records = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        records.append(data)
                    except json.JSONDecodeError:
                        continue
        return records
    
    def transform_record(self, model_id: str, attrs: dict) -> dict:
        """转换单条记录 - 保持原始数据完全一致"""
        # 元数据（从attrs中提取，如果不存在则用默认值）
        metadata = {
            'annotated': attrs.get('annotated', False),
            'uid': attrs.get('uid', ''),
            'score': attrs.get('score', 1),
        }
        
        # 业务数据 - 保持原始JSONL中的所有字段
        business_data = {}
        for key, value in attrs.items():
            # 跳过元数据字段
            if key in ['annotated', 'uid', 'score']:
                continue
            
            # placement: 数组转字符串（UI显示需要）
            if key == 'placement' and isinstance(value, list):
                business_data[key] = ', '.join(value)
            else:
                # 其他字段保持原样
                business_data[key] = value
        
        # 只添加 image_url（新增字段）
        business_data['image_url'] = self.build_gif_path(model_id)
        
        return metadata, business_data
    
    def import_to_db(self, source: str, db_path: str, clean: bool = False, batch_size: int = 1000):
        """导入数据到数据库"""
        print(f"\n{'='*60}")
        print(f"开始导入数据")
        print(f"{'='*60}")
        print(f"📂 数据源: {source}")
        print(f"🗄️  数据库: {db_path}")
        
        # 初始化数据库
        engine = get_engine(db_path)
        if clean:
            print("🗑️  清空数据库...")
            Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        
        session = get_session(db_path)
        
        try:
            print(f"📖 解析数据...")
            records = self.parse_jsonl(source)
            print(f"✓ 找到 {len(records)} 条记录")
            
            for idx, record in enumerate(records, 1):
                try:
                    # 获取 model_id 和属性
                    model_id = list(record.keys())[0]
                    attrs = record[model_id]
                    
                    # 转换数据
                    metadata, business_data = self.transform_record(model_id, attrs)
                    
                    # 检查是否存在
                    existing = session.query(Annotation).filter_by(model_id=model_id).first()
                    
                    if existing:
                        # 更新
                        existing.annotated = metadata['annotated']
                        existing.uid = metadata['uid']
                        existing.score = metadata['score']
                        existing.data = business_data
                        self.stats['updated'] += 1
                    else:
                        # 新增
                        annotation = Annotation(
                            model_id=model_id,
                            annotated=metadata['annotated'],
                            uid=metadata['uid'],
                            score=metadata['score'],
                            data=business_data
                        )
                        session.add(annotation)
                        self.stats['imported'] += 1
                    
                    # 批量提交
                    if idx % batch_size == 0:
                        session.commit()
                        print(f"  已处理 {idx} 条...")
                
                except Exception as e:
                    self.stats['errors'] += 1
                    if self.stats['errors'] <= 5:
                        print(f"⚠️  第 {idx} 条错误: {e}")
            
            session.commit()
            
            # 打印统计
            print(f"\n{'='*60}")
            print(f"✅ 导入完成！")
            print(f"{'='*60}")
            print(f"📊 统计:")
            print(f"  - 新增: {self.stats['imported']} 条")
            print(f"  - 更新: {self.stats['updated']} 条")
            print(f"  - 错误: {self.stats['errors']} 条")
            print(f"{'='*60}\n")
            
        except Exception as e:
            session.rollback()
            print(f"❌ 导入失败: {e}")
            raise
        finally:
            session.close()


def main():
    """命令行入口"""
    print("\n" + "="*70)
    print("⚠️  注意：此导入器已过时")
    print("="*70)
    print("推荐使用通用导入器：python -m importers.generic_importer --task annotation")
    print("通用导入器支持所有任务，功能更强大，维护更简单")
    print("="*70 + "\n")
    
    parser = argparse.ArgumentParser(description='导入物体属性标注数据')
    
    default_source = os.path.join(project_root, 'merged_attributes.jsonl')
    default_db = os.path.join(project_root, 'databases/annotation.db')
    
    parser.add_argument('--source', '-s', type=str, default=default_source,
                       help=f'数据源文件（默认: merged_attributes.jsonl）')
    parser.add_argument('--db', '-d', type=str, default=default_db,
                       help=f'数据库路径（默认: databases/annotation.db）')
    parser.add_argument('--clean', '-c', action='store_true',
                       help='清空数据库后导入')
    
    args = parser.parse_args()
    
    # 创建导入器并执行
    importer = AnnotationImporter()
    importer.import_to_db(
        source=args.source,
        db_path=args.db,
        clean=args.clean
    )
    
    print(f"✅ 可以运行: python src/main_multi.py --uid user1\n")


if __name__ == "__main__":
    main()
