#!/bin/bash
cd /root/projects/object_attributes_annotation_tool/modular_version

echo "=== 测试程序启动 ==="
conda run -n tool python -c "
import sys
sys.path.insert(0, '.')
from src.component_factory import ComponentFactory
from ui_configs import annotation_config

print('✅ 模块导入成功')

# 测试组件工厂
factory = ComponentFactory()
print(f'✅ 组件工厂创建成功')
print(f'   - 注册组件类型: {list(factory.component_registry.keys())}')

# 测试配置
print(f'✅ 配置加载成功')
print(f'   - 组件数量: {len(annotation_config.COMPONENTS)}')
print(f'   - 布局类型: {annotation_config.LAYOUT_CONFIG.get(\"type\")}')

print('\\n🎉 所有基础测试通过！')
"

