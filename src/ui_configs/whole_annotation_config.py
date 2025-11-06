"""
整体物体标注任务配置
简化版：消除冗余，配置更清晰
"""

# ============ 任务信息 ============
TASK_INFO = {
    "task_id": "whole_annotation",
    "task_name": "整体物体标注",
    "description": "标注整体物体的名称、尺寸和描述信息"
}

# ============ 组件配置 ============
# 设计原则：
# - id 使用数据字段名（简洁、语义明确）
# - type 描述组件类型（image, textbox, html 等）
# - id 默认等于 data_field（消除冗余）
COMPONENTS = [
    # --- 任务特定组件 ---
    # 图片显示
    {
        "id": "image_url",
        "type": "image",
        "label": "GIF预览",
        "interactive": False
    },
    # 属性字段
    {
        "id": "object_name",
        "type": "textbox",
        "label": "物体名称",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
        "process": None
    },
    {
        "id": "dimension",
        "type": "textbox",
        "label": "尺寸",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
        "placeholder": "例如: 0.78*0.41*0.54",
        "process": None,
        "data_field": "dimension"
    },
    # 尺度滑块
    {
        "id": "scale_slider",
        "type": "slider",
        "label": "🔧 尺度调整",
        "minimum": 0.01,
        "maximum": 2.0,
        "value": 1.0,
        "step": 0.01,
        "target_field": "dimension"
    },
    {
        "id": "overall_description",
        "type": "textbox",
        "label": "总体描述",
        "lines": 5,
        "has_checkbox": True,
        "checkbox_label": "✗",
        "process": "array_to_string"
    }
]

# ============ 布局配置 ============
# 布局定义：搜索栏在顶部，下面是两栏布局（GIF + 字段）
LAYOUT_CONFIG = {
    "type": "hstack",
    "elem_id": "main_content_row",
    "children": [
        # 左栏：GIF预览
        {
            "type": "vstack",
            "elem_id": "left_column",
            "children": ["image_url"]
        },
        
        # 右栏：字段
        {
            "type": "vstack",
            "elem_id": "right_column",
            "children": [
                # 属性字段
                "object_name",
                {
                    "type": "vstack",
                    "elem_id": "dimension_block",
                    "children": [
                        "dimension",
                        "scale_slider"  # 尺度滑块紧跟dimension
                    ]
                },
                "overall_description",
                # 进度
                "progress_box"
            ]
        }
    ]
}

# ============ UI配置 ============
UI_CONFIG = {
    "title": "整体物体标注"
}

# ============ 任务特定CSS ============
CUSTOM_CSS = """
/* 主内容行：左右列等高 */
#main_content_row {
    display: flex !important;
    align-items: stretch !important;
    gap: 16px !important;
    width: 100% !important;
}
#main_content_row > .gradio-column {
    display: flex !important;
    flex-direction: column !important;
    min-width: 0 !important;
}

/* 左侧列：GIF */
#left_column {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 0 !important;
    min-width: 320px !important;
}

/* GIF容器：固定高度，图片居中 */
#image_url {
    display: flex !important;
    flex: 1 1 auto !important;
    width: 100% !important;
    min-height: 600px !important;
}
#image_url .gradio-image {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: rgba(0, 0, 0, 0.03);
    border-radius: 12px;
}
#image_url .gradio-image > div {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
#image_url .gradio-image > div > img {
    max-height: 100% !important;
    max-width: 100% !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
    display: block !important;
}

/* 右侧信息列：自动填充空间 */
#right_column {
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
}
#right_column > .gradio-column {
    display: flex !important;
    flex-direction: column !important;
    width: 100% !important;
    gap: 0px !important;
}
#right_column > .gradio-row:last-child {
    margin-top: 12px !important;
}
#right_column .gradio-textbox {
    width: 100% !important;
}
#right_column .gradio-textbox textarea {
    width: 100% !important;
}

/* 字段标签与复选框视觉对齐 */
#right_column div[id$="_checkbox"] {
    margin-bottom: 4px !important;
}
#right_column div[id$="_checkbox"] .gradio-checkbox {
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    margin: 0 !important;
}
#right_column label {
    white-space: nowrap !important;
}

/* 尺寸与尺度组合块 */
#dimension_block {
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
    padding: 12px 14px !important;
    background: rgba(0, 0, 0, 0.02);
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 10px;
}
#dimension_block > .gradio-column,
#dimension_block > .gradio-row {
    width: 100% !important;
}
#dimension_block #dimension {
    margin-bottom: 0 !important;
}
#dimension_block #scale_slider {
    width: 100% !important;
}
#dimension_block .gradio-slider {
    width: 100% !important;
}
#dimension_checkbox {
    display: none !important;
}
"""

