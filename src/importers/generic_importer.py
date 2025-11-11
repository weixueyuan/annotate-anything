#!/usr/bin/env python
"""
通用数据导入器

支持导入任何标准 JSONL 格式的数据到数据库
适用于所有任务：annotation, whole_annotation, part_annotation 等

使用方式：
    # 导入所有任务（默认清空）
    python -m importers.generic_importer
    
    # 增量导入所有任务
    python -m importers.generic_importer --incremental
    
    # 按任务名导入（默认清空）
    python -m importers.generic_importer --task whole_annotation
    
    # 按任务名增量导入
    python -m importers.generic_importer --task annotation --incremental
    
    # 自定义路径
    python -m importers.generic_importer --source data.jsonl --db databases/custom.db
"""

import json
import os
import sys
import argparse
from pathlib import Path

# 添加项目路径
# generic_importer.py -> importers/ -> src/ -> modular_version/
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.db_models import Annotation, get_session, get_engine, Base


# 任务配置映射（默认路径）
TASK_CONFIGS = {
    'annotation': {
        'source': 'database_jsonl/merged_attributes.jsonl',
        'db': 'databases/annotation.db',
        'description': '物体属性标注',
        # 'base_path': '/mnt/data'  # 默认图片基础路径
    },
    'whole_annotation': {
        'source': 'database_jsonl/whole_annotation.jsonl',
        'db': 'databases/whole_annotation.db',
        'description': '整体物体标注',
        'base_path': '/mnt/inspurfs/IDC_t/lvzhaoyang_group/digital_content/lianxinyu/datasets/partnet_mobility_by_category_processed'  # 默认图片基础路径
    },
    'part_annotation': {
        'source': 'database_jsonl/part_annotation.jsonl',
        'db': 'databases/part_annotation.db',
        'description': '部件标注',
        'base_path': '/mnt/inspurfs/IDC_t/lvzhaoyang_group/digital_content/lianxinyu/datasets/partnet_mobility_by_category_processed'  # 默认图片基础路径
    },
    'test': {
        'source': 'database_jsonl/test.jsonl',
        'db': 'databases/test.db',
        'description': '测试数据',
        # 'base_path': '/mnt/data'  # 默认图片基础路径
    }
}


class GenericImporter:
    """通用数据导入器"""
    
    def __init__(self):
        self.stats = {'imported': 0, 'updated': 0, 'errors': 0}
    
    def parse_jsonl(self, filepath: str):
        """解析JSONL文件"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        records = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        records.append(data)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  第 {line_num} 行 JSON 解析错误: {e}")
                        continue
        return records
    
    def transform_record(self, model_id: str, attrs: dict, base_path: str = None) -> tuple:
        """
        转换单条记录 - 通用处理
        
        自动识别和处理：
        - 元数据字段（annotated, uid, score）
        - 数组字段（自动转为换行符分隔的字符串）
        - 图片路径字段（自动拼接基础路径）
        - 其他字段保持原样
        
        Args:
            model_id: 模型ID
            attrs: 属性字典
            base_path: 图片路径的基础路径，如果提供则会拼接到相对路径前
        """
        # 元数据（从attrs中提取，如果不存在则用默认值）
        metadata = {
            'annotated': attrs.get('annotated', False),
            'uid': attrs.get('uid', ''),
            'score': attrs.get('score', 1),
        }
        
        # 业务数据 - 通用处理
        business_data = {}
        for key, value in attrs.items():
            # 跳过元数据字段
            if key in ['annotated', 'uid', 'score']:
                continue
            
            # 处理图片路径字段
            if key.startswith('image_url') and isinstance(value, str) and base_path and not value.startswith('/'):
                # 拼接基础路径和相对路径
                business_data[key] = os.path.join(base_path, value)
                print(f"  处理图片路径: {key} = {business_data[key]}")
            # 自动处理数组字段：转为字符串
            elif isinstance(value, list):
                # 如果是字符串数组，用换行符连接
                if value and isinstance(value[0], str):
                    business_data[key] = '\n'.join(value)
                # 如果是其他类型的数组，用逗号连接
                else:
                    business_data[key] = ', '.join(str(v) for v in value)
            else:
                # 其他字段保持原样
                business_data[key] = value
        
        return metadata, business_data
    
    def import_to_db(self, source: str, db_path: str, clean: bool = False, batch_size: int = 1000, base_path: str = None):
        """
        导入数据到数据库
        
        Args:
            source: 源数据文件路径
            db_path: 数据库文件路径
            clean: 是否清空数据库
            batch_size: 批处理大小
            base_path: 图片路径的基础路径，如果提供则会拼接到相对路径前
        """
        print(f"\n{'='*60}")
        print(f"开始导入数据")
        print(f"{'='*60}")
        print(f"📂 数据源: {source}")
        print(f"🗄️  数据库: {db_path}")
        if base_path:
            print(f"🖼️  图片基础路径: {base_path}")
        
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
                    if not record:
                        continue
                    
                    model_id = list(record.keys())[0]
                    attrs = record[model_id]
                    
                    # 转换数据
                    metadata, business_data = self.transform_record(model_id, attrs, base_path)
                    
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
            
            # 查询并打印第一条记录，用于验证
            try:
                first_record = session.query(Annotation).first()
                if first_record:
                    print(f"\n📝 第一条记录示例:")
                    print(f"  - ID: {first_record.model_id}")
                    print(f"  - 标注状态: {'已标注' if first_record.annotated else '未标注'}")
                    print(f"  - 用户: {first_record.uid or '无'}")
                    print(f"  - 数据:")
                    
                    # 打印数据字段（最多显示前5个字段）
                    if first_record.data:
                        for i, (key, value) in enumerate(first_record.data.items()):
                            if i >= 5:
                                print(f"      ... (还有 {len(first_record.data) - 5} 个字段)")
                                break
                            
                            # 对于长字符串，只显示前50个字符
                            if isinstance(value, str) and len(value) > 50:
                                value_display = value[:50] + "..."
                            else:
                                value_display = value
                                
                            print(f"      {key}: {value_display}")
                            
                            # 特别关注图片URL字段
                            if key.startswith('image _url'):
                                print(f"        (图片路径已处理: {'是' if base_path and not value.startswith('/') else '否'})")
            except Exception as e:
                print(f"⚠️ 无法打印示例记录: {e}")
                
            print(f"{'='*60}\n")
            
        except Exception as e:
            session.rollback()
            print(f"❌ 导入失败: {e}")
            raise
        finally:
            session.close()


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='通用数据导入器 - 支持所有标准 JSONL 格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 导入所有任务（默认清空）
  python -m importers.generic_importer

  # 增量导入所有任务
  python -m importers.generic_importer --incremental
  
  # 按任务名导入（默认清空）
  python -m importers.generic_importer --task annotation
  
  # 按任务名增量导入
  python -m importers.generic_importer --task annotation --incremental
  
  # 自定义路径
  python -m importers.generic_importer --source data.jsonl --db databases/custom.db

支持的任务:
"""
    )
    
    # 添加任务列表到帮助信息
    for task_name, config in TASK_CONFIGS.items():
        parser.epilog += f"  {task_name:20s} - {config['description']}\n"
    
    parser.add_argument('--task', '-t', type=str, choices=list(TASK_CONFIGS.keys()),
                       help='任务名称（自动使用默认路径）')
    parser.add_argument('--source', '-s', type=str,
                       help='数据源文件（JSONL格式）')
    parser.add_argument('--db', '-d', type=str,
                       help='数据库路径')
    parser.add_argument('--incremental', '-i', action='store_true',
                       help='增量导入（不清除旧数据），默认为清空导入')
    parser.add_argument('--list', '-l', action='store_true',
                       help='列出所有支持的任务')
    parser.add_argument('--base-path', '-b', type=str,
                       help='图片路径的基础路径，用于拼接相对路径')
    
    args = parser.parse_args()
    
    # 列出任务
    if args.list:
        print("\n📋 支持的任务:")
        print("=" * 70)
        for task_name, config in TASK_CONFIGS.items():
            print(f"\n任务名称: {task_name}")
            print(f"  描述: {config['description']}")
            print(f"  数据源: {config['source']}")
            print(f"  数据库: {config['db']}")
        print("\n" + "=" * 70)
        print("\n使用方式: python -m importers.generic_importer --task <任务名>\n")
        return
    
    # 确定导入模式
    clean_mode = not args.incremental
    
    # 如果没有指定任何参数，则导入所有任务
    if not args.task and not args.source and not args.db:
        print(f"\n🚀 默认执行：导入所有任务 ({'清空模式' if clean_mode else '增量模式'})")
        importer = GenericImporter()
        for task_name, config in TASK_CONFIGS.items():
            importer.stats = {'imported': 0, 'updated': 0, 'errors': 0} # 重置统计
            print(f"\n---\n🔄 正在处理任务: {task_name}...")
            source = os.path.join(project_root, config['source'])
            db_path = os.path.join(project_root, config['db'])
            
            if not os.path.exists(source):
                print(f"⚠️  警告: 数据源不存在，跳过: {source}")
                continue
            
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            # 使用任务配置中的基础路径，如果命令行参数有指定则优先使用命令行参数
            base_path = args.base_path or config.get('base_path')
            importer.import_to_db(source=source, db_path=db_path, clean=clean_mode, base_path=base_path)
        
        print("\n🎉 所有任务导入完成！\n")
        return

    # 处理单个任务或自定义路径
    source, db_path = None, None
    if args.task:
        if args.source or args.db:
            parser.error("使用 --task 时，不应再指定 --source 或 --db")
        task_config = TASK_CONFIGS[args.task]
        source = os.path.join(project_root, task_config['source'])
        db_path = os.path.join(project_root, task_config['db'])
        print(f"\n📝 使用任务配置: {args.task} - {task_config['description']}")
    
    elif args.source and args.db:
        source = args.source
        db_path = args.db
    
    else:
        parser.error("请指定 --task，或同时指定 --source 和 --db，或不带参数运行以导入所有任务")

    # 检查和执行
    if not os.path.exists(source):
        print(f"\n❌ 错误: 数据源文件不存在: {source}")
        return
    
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    importer = GenericImporter()
    
    # 获取基础路径：优先使用命令行参数，其次使用任务配置（如果是任务模式）
    base_path = args.base_path
    if not base_path and args.task:
        base_path = TASK_CONFIGS[args.task].get('base_path')
    
    importer.import_to_db(source=source, db_path=db_path, clean=clean_mode, base_path=base_path)
    
    if args.task:
        print(f"✅ 可以运行: python src/main_multi.py --task {args.task} --dev --uid user1\n")
    else:
        print(f"✅ 导入完成！\n")


if __name__ == "__main__":
    main()

