# 配置文件示例和说明

## 快速示例

假设你要创建一个简单的图片标注界面，包含：
- 左侧：图片预览
- 右侧：标题、描述、标签字段

### 1. 定义组件 (COMPONENTS)

```python
COMPONENTS = [
    # 图片预览
    {
        "id": "image_box",       # 唯一标识
        "type": "image",         # 组件类型
        "label": "图片预览",
        "interactive": False
    },
    
    # 标题字段（带复选框）
    {
        "id": "title",
        "type": "textbox",
        "label": "标题",
        "lines": 1,
        "has_checkbox": True,    # 标注时可以打勾确认
        "checkbox_label": "✓"
    },
    
    # 描述字段（多行，带复选框）
    {
        "id": "description",
        "type": "textbox",
        "label": "描述",
        "lines": 3,
        "has_checkbox": True,
        "checkbox_label": "✓"
    },
    
    # 标签字段
    {
        "id": "tags",
        "type": "textbox",
        "label": "标签",
        "lines": 1,
        "placeholder": "例如: 动物, 户外, 自然"
    },
    
    # 保存按钮
    {
        "id": "save_btn",
        "type": "button",
        "label": "💾 保存",
        "variant": "primary"
    }
]
```

### 2. 定义布局 (LAYOUT_CONFIG)

```python
LAYOUT_CONFIG = {
    "type": "two_column",        # 两栏布局
    "elem_id": "main_row",       # CSS ID
    "left_scale": 1,             # 左栏占1份
    "right_scale": 1,            # 右栏占1份
    
    # 左栏：只有图片
    "left": ["image_box"],
    
    # 右栏：字段从上到下排列
    "right": {
        "type": "vstack",        # 垂直堆叠
        "children": [
            "title",             # 顺序决定显示位置
            "description",
            "tags",
            "save_btn"
        ]
    }
}
```

### 3. 渲染结果

```
┌──────────────────────────────────────────┐
│  图片标注界面                               │
├───────────────────┬──────────────────────┤
│                   │  标题                 │
│                   │  [________] ✓         │
│   [图片预览]       │                      │
│                   │  描述                 │
│                   │  [________]           │
│                   │  [________] ✓         │
│                   │  [________]           │
│                   │                      │
│                   │  标签                 │
│                   │  [________]           │
│                   │                      │
│                   │  [💾 保存]            │
└───────────────────┴──────────────────────┘
```

## 复杂示例：嵌套布局

如果你需要更复杂的布局，比如搜索栏在顶部：

```python
LAYOUT_CONFIG = {
    "type": "two_column",
    "elem_id": "main_row",
    "left_scale": 1,
    "right_scale": 1,
    
    "left": ["image_box"],
    
    "right": {
        "type": "vstack",
        "children": [
            # 顶部：搜索栏（水平布局）
            {
                "type": "hstack",
                "elem_id": "search_bar",
                "children": ["search_box", "search_btn"]
            },
            
            # 中间：字段区域（垂直布局）
            {
                "type": "vstack",
                "elem_id": "fields_area",
                "children": ["title", "description", "tags"]
            },
            
            # 底部：按钮行（水平布局）
            {
                "type": "hstack",
                "elem_id": "button_row",
                "children": ["prev_btn", "save_btn", "next_btn"]
            }
        ]
    }
}
```

渲染结果：
```
┌──────────────────────────────────────────┐
│                   │  [搜索框] [搜索按钮]    │
│                   ├──────────────────────┤
│   [图片预览]       │  标题                 │
│                   │  描述                 │
│                   │  标签                 │
│                   ├──────────────────────┤
│                   │  [⬅️] [💾] [➡️]      │
└───────────────────┴──────────────────────┘
```

## 配置字段说明

### 组件通用字段
- `id` (必需)：唯一标识符，同时用作 elem_id
- `type` (必需)：组件类型
- `label`：显示标签
- `data_field` (可选)：对应的数据库字段名
  - 如果不指定，默认使用 `id` 作为字段名
  - 用于将数据库数据映射到UI组件
  - 特殊值：`_computed_*` 表示计算字段

### data_field 映射关系

`data_field` 连接了**数据库字段**和**UI组件**：

```python
# 配置文件
{
    "id": "gif_box",               # 组件ID（前端）
    "type": "image",
    "data_field": "image_url"      # 数据库字段（后端）
}

# 数据库中
{
    "model_id": "xxx",
    "image_url": "/path/to/img.gif",  # 这个字段的值会显示在 gif_box 组件中
    "category": "furniture"
}

# 运行时
load_data() 函数读取 attrs['image_url'] → 赋值给 gif_box 组件
```

**约定**：
- 不指定 `data_field` 时，默认 `data_field = id`
- 字段组件（带 `has_checkbox`）自动使用 `id` 作为字段名
- 特殊组件需要明确指定（如 image, model_id）

### 类型特定字段

#### image
```python
{
    "id": "image_box",
    "type": "image",
    "label": "图片",
    "interactive": False,          # 是否可编辑
    "data_field": "image_url"      # 对应数据库的字段名
}
```

**多图片示例**：
```python
COMPONENTS = [
    {
        "id": "front_view",
        "type": "image",
        "label": "正面图",
        "data_field": "front_image_url"
    },
    {
        "id": "side_view",
        "type": "image",
        "label": "侧面图",
        "data_field": "side_image_url"
    },
    {
        "id": "top_view",
        "type": "image",
        "label": "俯视图",
        "data_field": "top_image_url"
    }
]
```

#### textbox
```python
{
    "id": "field_name",
    "type": "textbox",
    "label": "字段标签",
    "lines": 1,                    # 行数
    "placeholder": "提示文本",
    "has_checkbox": True,          # 是否带复选框
    "checkbox_label": "✓",         # 复选框标签
    "process": "array_to_string",  # 数据处理方式
    "data_field": "field_name"     # 数据库字段（默认使用id）
}
```

#### button
```python
{
    "id": "save_btn",
    "type": "button",
    "label": "保存",
    "variant": "primary"           # primary, secondary, stop
}
```

#### slider
```python
{
    "id": "scale_slider",
    "type": "slider",
    "label": "缩放",
    "minimum": 0,
    "maximum": 1,
    "value": 0.5,
    "step": 0.01
}
```

#### html
```python
{
    "id": "status_box",
    "type": "html",
    "value": "<div>状态信息</div>"
}
```

#### checkbox
```python
{
    "id": "agree_checkbox",
    "type": "checkbox",
    "label": "我同意",
    "value": False
}
```

## 布局配置说明

### two_column 布局
```python
{
    "type": "two_column",
    "elem_id": "main_row",         # CSS ID
    "left_scale": 1,               # 左栏宽度比例
    "right_scale": 2,              # 右栏宽度比例（2:1）
    "left": [...],                 # 左栏组件列表
    "right": {...}                 # 右栏布局（可嵌套）
}
```

### vstack (垂直堆叠)
```python
{
    "type": "vstack",
    "elem_id": "my_column",        # 可选：CSS ID
    "children": [                  # 从上到下排列
        "component1",
        "component2",
        {...}                       # 可嵌套
    ]
}
```

### hstack (水平堆叠)
```python
{
    "type": "hstack",
    "elem_id": "my_row",           # 可选：CSS ID
    "children": [                  # 从左到右排列
        "component1",
        "component2",
        {...}                       # 可嵌套
    ]
}
```

## CSS 样式控制

通过 `elem_id` 控制样式：

```python
# 配置
{
    "type": "hstack",
    "elem_id": "button_row",
    "children": ["btn1", "btn2", "btn3"]
}
```

```css
/* CSS */
#button_row {
    display: flex !important;
    justify-content: space-between !important;
    gap: 8px !important;
}

#button_row button {
    flex: 1 !important;
    min-width: 100px !important;
}
```

## 最佳实践

### 1. 命名约定
- 使用有意义的 `id`：`search_box`, `title_field`, `save_btn`
- 避免缩写：`desc` ❌ → `description` ✅
- 保持一致性：`_box`, `_btn`, `_field` 等后缀

### 2. 布局设计
- 优先使用 `two_column` 作为主布局
- 使用 `vstack` 组织字段
- 使用 `hstack` 组织按钮行

### 3. 组件顺序
- 重要字段放在顶部
- 按钮放在底部
- 保持视觉流畅性

### 4. CSS控制
- 只对关键容器添加 `elem_id`
- 避免过度使用内联样式
- 使用 CSS 文件统一管理样式

## 调试技巧

### 1. 检查组件是否创建
```python
factory = ComponentFactory()
factory.build_layout(COMPONENTS, LAYOUT_CONFIG)
print("创建的组件:", factory.get_all_components().keys())
```

### 2. 验证布局结构
在浏览器中检查 HTML 结构，确认 `elem_id` 是否正确生成。

### 3. CSS 不生效？
- 检查 `elem_id` 是否正确
- 使用 `!important` 覆盖默认样式
- 检查选择器优先级

---

**提示**：配置文件应该像文档一样易读。如果你发现配置难以理解，可能需要重新组织结构。

