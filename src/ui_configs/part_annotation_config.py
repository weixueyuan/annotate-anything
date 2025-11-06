"""
部件标注任务配置
特殊布局：三张图片横向排列，标注字段左右两栏布局
"""

# ============ 任务信息 ============
TASK_INFO = {
    "task_id": "part_annotation",
    "task_name": "部件标注",
    "description": "标注物体部件的详细属性信息"
}

# ============ 组件配置 ============
COMPONENTS = [
    # 三张图片
    {
        "id": "image_url",
        "type": "image",
        "label": "物体视图",
        "interactive": False
    },
    {
        "id": "image_url_p1",
        "type": "image",
        "label": "部件高亮渲染视图",
        "interactive": False
    },
    {
        "id": "image_url_p2",
        "type": "image",
        "label": "部件材质渲染视图",
        "interactive": False
    },
    
    # 标注字段
    {
        "id": "object_name",
        "type": "textbox",
        "label": "物体名称",
        "lines": 1,
        "interactive": False,
    },
    {
        "id": "object_dimension",
        "type": "textbox",
        "label": "物体尺寸(长✖️宽✖️高)",
        "lines": 1,
        "placeholder": "例如: 0.78*0.41*0.54",
        "interactive": False,
    },
    {
        "id": "label",
        "type": "textbox",
        "label": "部件名称",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
    },
    {
        "id": "material",
        "type": "textbox",
        "label": "材质",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
    },
    {
        "id": "density",
        "type": "textbox",
        "label": "密度",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
        "placeholder": "例如: 600 kg/m^3",
    },
    {
        "id": "mass",
        "type": "textbox",
        "label": "质量",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
        "placeholder": "例如: 25 kg",
    },
]

# ============ 布局配置 ============
LAYOUT_CONFIG = {
    "type": "tree",
    "children": [
        # 第二行：三张图片横向排列
        {
            "type": "hstack",
            "elem_id": "images_row",
            "children": ["image_url", "image_url_p1", "image_url_p2"]
        },
        
        # 第三行：标注字段（左右两栏布局）
        {
            "type": "hstack",
            "elem_id": "fields_row",
            "children": [
                # 左栏
                {
                    "type": "vstack",
                    "elem_id": "left_column",
                    "children": [
                        "object_name",
                        "object_dimension",
                        "label",
                    ]
                },
                # 右栏
                {
                    "type": "vstack",
                    "elem_id": "right_column",
                    "children": [
                        "material",
                        "density",
                        "mass"
                    ]
                }
            ]
        },
        # 进度显示（放在主内容下方）
        "progress_box"
    ]
}

# ============ UI配置 ============
UI_CONFIG = {
    "title": "部件标注工具",
}

# ============ 任务特定CSS ============
CUSTOM_CSS = """
/* 图片行：三张图片横向排列 */
#images_row {
    display: flex !important;
    gap: 12px !important;
    width: 100% !important;
    margin-top: 12px !important;
    margin-bottom: 12px !important;
}
#images_row > .gradio-column {
    flex: 1 !important;
    min-width: 0 !important;
}
#images_row .gradio-image {
    width: 100% !important;
    height: 400px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: rgba(0, 0, 0, 0.03);
    border-radius: 12px;
}
#images_row .gradio-image > div {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
#images_row .gradio-image > div > img {
    max-height: 100% !important;
    max-width: 100% !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
    display: block !important;
}

/* 字段行：左右两栏 */
#fields_row {
    display: flex !important;
    gap: 16px !important;
    width: 100% !important;
}
#fields_row > .gradio-column {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
}

/* 左右栏样式 */
#left_column, #right_column {
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
}
#left_column > .gradio-column,
#right_column > .gradio-column {
    display: flex !important;
    flex-direction: column !important;
    width: 100% !important;
    gap: 0px !important;
}
#left_column .gradio-textbox,
#right_column .gradio-textbox {
    width: 100% !important;
}

/* 字段标签与复选框视觉对齐 */
#left_column div[id$="_checkbox"],
#right_column div[id$="_checkbox"] {
    margin-bottom: 4px !important;
}
#left_column div[id$="_checkbox"] .gradio-checkbox,
#right_column div[id$="_checkbox"] .gradio-checkbox {
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    margin: 0 !important;
}
#left_column label,
#right_column label {
    white-space: nowrap !important;
}
"""

