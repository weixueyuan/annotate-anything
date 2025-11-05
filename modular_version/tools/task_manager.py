#!/usr/bin/env python
"""
任务管理工具

用于创建和管理多个标注任务
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def list_tasks():
    """列出所有已配置的任务"""
    from src.routes import ROUTES
    
    print("\n📋 已配置的任务:")
    print("=" * 80)
    
    for idx, route in enumerate(ROUTES, 1):
        task_name = route['task']
        
        # 检查文件是否存在
        db_exists = os.path.exists(f"{project_root}/databases/{task_name}.db")
        config_exists = os.path.exists(f"{project_root}/src/ui_configs/{task_name}_config.py")
        
        status = "✅" if (db_exists and config_exists) else "⚠️ "
        
        print(f"\n{idx}. {status} {task_name}")
        print(f"   描述: {route['description']}")
        print(f"   端口: {route['port']}")
        print(f"   数据库: {'✅' if db_exists else '❌'} databases/{task_name}.db")
        print(f"   配置: {'✅' if config_exists else '❌'} src/ui_configs/{task_name}_config.py")
    
    print("\n" + "=" * 80)

def create_task(task_name, description, port, base_task="annotation"):
    """创建新任务"""
    
    print(f"\n🔧 创建新任务: {task_name}")
    print("=" * 80)
    
    # 1. 检查是否已存在
    from src.routes import ROUTES
    for route in ROUTES:
        if route['task'] == task_name:
            print(f"❌ 任务 '{task_name}' 已存在！")
            return False
    
    # 2. 创建UI配置文件
    base_config = f"{project_root}/src/ui_configs/{base_task}_config.py"
    new_config = f"{project_root}/src/ui_configs/{task_name}_config.py"
    
    if not os.path.exists(base_config):
        print(f"❌ 基础配置文件不存在: {base_config}")
        return False
    
    print(f"📄 复制配置文件...")
    shutil.copy(base_config, new_config)
    
    # 修改TASK_INFO
    with open(new_config, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换任务信息
    content = content.replace(
        f'"task_id": "{base_task}"',
        f'"task_id": "{task_name}"'
    )
    content = content.replace(
        f'"task_name": "物体属性标注"',
        f'"task_name": "{description}"'
    )
    
    with open(new_config, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 创建配置: src/ui_configs/{task_name}_config.py")
    
    # 3. 添加到routes.py
    routes_file = f"{project_root}/src/routes.py"
    with open(routes_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到ROUTES列表的结束位置
    insert_pos = None
    for i, line in enumerate(lines):
        if ']' in line and 'ROUTES' in ''.join(lines[max(0, i-10):i]):
            insert_pos = i
            break
    
    if insert_pos:
        # 添加新任务配置
        new_route = f"""    {{
        "url": "/{task_name}",
        "task": "{task_name}",
        "port": {port},
        "description": "{description}"
    }},
"""
        lines.insert(insert_pos, new_route)
        
        with open(routes_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"✅ 添加路由: routes.py")
    
    # 4. 提示创建数据库
    print(f"\n📊 下一步：准备数据")
    print("=" * 80)
    print(f"1. 准备 JSONL 格式的源数据文件")
    print(f"2. 运行导入命令:")
    print(f"   python -m importers.annotation_importer \\")
    print(f"       --source your_data.jsonl \\")
    print(f"       --db databases/{task_name}.db")
    print()
    print(f"3. 启动任务:")
    print(f"   python src/main_multi.py --task {task_name}")
    print("=" * 80)
    
    return True

def check_task(task_name):
    """检查任务配置完整性"""
    
    print(f"\n🔍 检查任务: {task_name}")
    print("=" * 80)
    
    issues = []
    
    # 检查配置文件
    config_file = f"{project_root}/ui_configs/{task_name}_config.py"
    if os.path.exists(config_file):
        print(f"✅ 配置文件存在: {config_file}")
    else:
        print(f"❌ 配置文件缺失: {config_file}")
        issues.append("配置文件")
    
    # 检查数据库
    db_file = f"{project_root}/databases/{task_name}.db"
    if os.path.exists(db_file):
        print(f"✅ 数据库存在: {db_file}")
        
        # 检查数据量
        try:
            from src.db_models import get_session, Annotation
            session = get_session(db_file)
            count = session.query(Annotation).count()
            session.close()
            print(f"   数据量: {count} 条")
        except Exception as e:
            print(f"   ⚠️  无法读取数据: {e}")
    else:
        print(f"❌ 数据库缺失: {db_file}")
        issues.append("数据库")
    
    # 检查routes.py
    from routes import ROUTES
    found = False
    for route in ROUTES:
        if route['task'] == task_name:
            found = True
            print(f"✅ routes.py 配置存在")
            print(f"   端口: {route['port']}")
            print(f"   描述: {route['description']}")
            break
    
    if not found:
        print(f"❌ routes.py 配置缺失")
        issues.append("路由配置")
    
    print("\n" + "=" * 80)
    
    if issues:
        print(f"⚠️  发现 {len(issues)} 个问题: {', '.join(issues)}")
        return False
    else:
        print(f"✅ 任务 '{task_name}' 配置完整，可以使用")
        return True

def main():
    parser = argparse.ArgumentParser(description='任务管理工具')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # list 命令
    subparsers.add_parser('list', help='列出所有任务')
    
    # create 命令
    create_parser = subparsers.add_parser('create', help='创建新任务')
    create_parser.add_argument('name', help='任务名称（英文，如: review）')
    create_parser.add_argument('--description', default='新任务', help='任务描述')
    create_parser.add_argument('--port', type=int, default=7861, help='端口号')
    create_parser.add_argument('--base', default='annotation', help='基于哪个任务复制配置')
    
    # check 命令
    check_parser = subparsers.add_parser('check', help='检查任务配置')
    check_parser.add_argument('name', help='任务名称')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_tasks()
    
    elif args.command == 'create':
        create_task(args.name, args.description, args.port, args.base)
    
    elif args.command == 'check':
        check_task(args.name)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

