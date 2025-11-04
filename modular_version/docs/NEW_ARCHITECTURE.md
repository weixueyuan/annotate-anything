# 新组件化架构说明

## 概述

新架构采用**配置驱动 + 组件工厂**的设计模式，消除了配置冗余，使代码更清晰、更易扩展。

## 核心设计原则

### 1. 消除冗余
- **`id` 既是 key 也是 elem_id**：一个标识符统一用于数据引用和CSS控制
- **移除 `order` 字段**：组件默认从上到下排序，顺序由配置列表决定
- **移除 `position` 字段**：位置由 `LAYOUT_CONFIG` 统一控制

### 2. 关注点分离
- **`COMPONENTS`**：只定义组件本身（类型、标签、属性）
- **`LAYOUT_CONFIG`**：只定义布局结构（左右分栏、垂直水平堆叠）
- **`elem_id`**：用于CSS精确控制样式

### 3. 约定优于配置
- 字段组件按配置顺序从上到下显示
- 布局采用树形嵌套结构（`vstack`/`hstack`）
- 组件类型标准化（image, textbox, html, button, slider, checkbox）

## 架构组成

### 1. 组件工厂 (`src/component_factory.py`)

**职责**：
- 根据配置动态创建Gradio组件
- 管理组件注册表
- 处理组件渲染和布局

**核心方法**：
```python
# 创建单个组件
factory.create_component(config)

# 构建整个布局
factory.build_layout(components_config, layout_config)

# 获取创建的组件
factory.get_component(comp_id)
factory.get_all_components()
```

### 2. 配置文件 (`ui_configs/annotation_config.py`)

#### 组件配置 (`COMPONENTS`)
定义所有UI组件：

```python
COMPONENTS = [
    {
        "id": "gif_box",          # 唯一标识（同时用作elem_id）
        "type": "image",          # 组件类型
        "label": "GIF预览",       # 显示标签
        "interactive": False      # 组件属性
    },
    {
        "id": "category",
        "type": "textbox",
        "label": "Category (类别)",
        "lines": 1,
        "has_checkbox": True,     # 是否带复选框
        "checkbox_label": "✗",
        "process": None           # 数据处理方式
    },
    # ... 更多组件
]
```

**字段说明**：
- `id`：组件唯一标识，同时用作 `elem_id`（CSS选择器）
- `type`：组件类型（image, textbox, html, button, slider, checkbox）
- `label`：显示标签
- `has_checkbox`：是否为带复选框的字段（用于标注确认）
- `process`：数据处理方式（如 `array_to_string`）

#### 布局配置 (`LAYOUT_CONFIG`)
定义UI布局结构：

```python
LAYOUT_CONFIG = {
    "type": "two_column",        # 布局类型
    "elem_id": "main_content_row",  # CSS ID
    "left_scale": 1,             # 左栏比例
    "right_scale": 2,            # 右栏比例
    
    # 左侧：GIF预览
    "left": ["gif_box"],
    
    # 右侧：树形嵌套结构
    "right": {
        "type": "vstack",        # 垂直堆叠
        "children": [
            # 水平堆叠（搜索行）
            {
                "type": "hstack",
                "elem_id": "search_row",
                "children": ["search_box", "status_box"]
            },
            
            # 字段组件（按顺序从上到下）
            "model_id_box",
            "category",
            "description",
            "material",
            "dimensions",
            "placement",
            
            # 其他组件
            "scale_slider",
            "progress_box",
            
            # 按钮行
            {
                "type": "hstack",
                "elem_id": "button_row",
                "children": ["prev_btn", "next_btn", "save_btn"]
            }
        ]
    }
}
```

**布局类型**：
- `two_column`：两栏布局（左右分栏）
- `tree`：树形嵌套布局（纯递归）

**容器类型**：
- `vstack`：垂直堆叠（对应 Gradio 的 `Column`）
- `hstack`：水平堆叠（对应 Gradio 的 `Row`）

### 3. 主程序 (`src/main_multi.py`)

**兼容性设计**：
- 自动检测配置格式（新/旧）
- 优先使用新配置（`COMPONENTS` + `LAYOUT_CONFIG`）
- 向下兼容旧配置（`FIELD_CONFIG`）

```python
# 配置检测逻辑
if hasattr(config_module, 'COMPONENTS') and hasattr(config_module, 'LAYOUT_CONFIG'):
    # 使用新架构
    return self.build_interface_v2()
else:
    # 使用旧架构（兼容）
    return self.build_interface()
```

## elem_id 和 CSS 的关系

### 1. elem_id 的作用
`elem_id` 是连接 Gradio 组件和 CSS 样式的桥梁：

```python
# 配置中定义
{
    "id": "search_row",
    "type": "hstack",
    "elem_id": "search_row"  # 生成 HTML 元素 id="search_row"
}
```

### 2. CSS 控制样式
通过 `elem_id` 精确控制样式：

```css
/* 控制搜索行的布局 */
#search_row {
    display: flex !important;
    align-items: stretch !important;
    width: 100% !important;
}

/* 控制右侧面板 */
#info_column {
    display: flex !important;
    flex-direction: column !important;
    gap: 4px !important;
}

/* 控制按钮行 */
#button_row {
    display: flex !important;
    justify-content: space-between !important;
}
```

### 3. 为什么需要 elem_id？
- **精确定位**：在复杂UI中精确控制特定元素
- **样式隔离**：避免样式冲突
- **布局控制**：Flexbox、Grid等高级布局
- **响应式设计**：媒体查询针对特定元素

## 优势对比

### 旧架构
```python
FIELD_CONFIG = [
    {
        "key": "category",           # 数据key
        "label": "Category (类别)",
        "type": "textbox",
        "lines": 1,
        "has_checkbox": True,
        "placeholder": "",
        "flex": 1,                   # 布局信息
        "process": None,
        "order": 1,                  # 冗余：顺序
        "position": "right",         # 冗余：位置
        "elem_id": "category_field"  # 冗余：单独定义
    }
]
```

### 新架构
```python
COMPONENTS = [
    {
        "id": "category",            # 一个标识符多用途
        "type": "textbox",
        "label": "Category (类别)",
        "lines": 1,
        "has_checkbox": True,
        "process": None
    }
]

LAYOUT_CONFIG = {
    "right": {
        "children": ["category", ...]  # 位置在这里定义
    }
}
```

**改进点**：
- ✅ 减少 50% 的配置代码
- ✅ 消除 `key`/`elem_id` 冗余
- ✅ 移除 `order`/`position` 冗余
- ✅ 关注点分离（组件定义 vs 布局）
- ✅ 更灵活的嵌套布局

## 扩展指南

### 添加新组件类型
1. 在 `ComponentFactory` 中注册：
```python
self.component_registry = {
    # ... 现有类型
    "new_type": self._create_new_type
}
```

2. 实现创建方法：
```python
def _create_new_type(self, config: Dict):
    return gr.NewComponent(
        label=config.get("label", ""),
        elem_id=config.get("id")
    )
```

### 添加新布局类型
1. 在 `build_layout` 中添加分支：
```python
elif layout_type == "new_layout":
    return self._build_new_layout(layout_config)
```

2. 实现布局方法：
```python
def _build_new_layout(self, config: Dict):
    # 自定义布局逻辑
    pass
```

### 添加新任务
1. 创建配置文件：`ui_configs/new_task_config.py`
2. 定义 `COMPONENTS` 和 `LAYOUT_CONFIG`
3. 在 `routes.py` 中注册任务
4. 启动：`python src/main_multi.py --task new_task`

## 总结

新架构通过**约定优于配置**和**关注点分离**的原则，实现了：
- 🎯 **更清晰**：配置结构一目了然
- 🚀 **更简洁**：消除冗余，代码量减半
- 🔧 **更灵活**：树形嵌套支持任意复杂布局
- 📦 **更易扩展**：添加组件/布局/任务都很简单
- 🎨 **更易维护**：CSS和配置解耦，修改互不影响

---

**设计者笔记**：这个架构的核心思想是"让配置文件像用户手册一样易读"。当你看到配置时，应该能立即理解UI的结构，而不需要在脑海中解析复杂的映射关系。

