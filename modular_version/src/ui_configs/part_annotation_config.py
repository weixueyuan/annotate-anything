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
    # Model ID 和状态（第一行）
    {
        "id": "model_id",
        "type": "search",
        "label": "🔍 Model ID（可搜索）",
        "placeholder": "显示当前ID，可输入其他ID，必须按回车键才能搜索",
        "lines": 1,
        "searchable": True,
        "search_field": "model_id"
    },
    {
        "id": "annotation_status",
        "type": "html",
        "value": "",
        "data_field": "_computed_status"
    },
    
    # 三张图片（第二行）
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
    
    # 标注字段（左栏）
    {
        "id": "object_name",
        "type": "textbox",
        "label": "物体名称",
        "lines": 1,
        # "has_checkbox": True,
        # "checkbox_label": "✗",
        "column": "left",
        "interactive": False,  # 设置为不可编辑
    },
    {
        "id": "object_dimension",
        "type": "textbox",
        "label": "物体尺寸(长✖️宽✖️高)",
        "lines": 1,
        # "has_checkbox": True,
        # "checkbox_label": "✗",
        "placeholder": "例如: 0.78*0.41*0.54",
        "column": "left",
        "interactive": False,  # 设置为不可编辑
    },
    {
        "id": "label",
        "type": "textbox",
        "label": "部件名称",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
        "column": "left"
    },
    {
        "id": "material",
        "type": "textbox",
        "label": "材质",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
        "column": "right"
    },
    {
        "id": "density",
        "type": "textbox",
        "label": "密度",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
        "placeholder": "例如: 600 kg/m^3",
        "column": "right"
    },
    {
        "id": "mass",
        "type": "textbox",
        "label": "质量",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
        "placeholder": "例如: 25 kg",
        "column": "right"
    },
    
    # 进度显示
    {
        "id": "progress_box",
        "type": "textbox",
        "label": "进度",
        "lines": 1
    },
    
    # 按钮
    {
        "id": "prev_btn",
        "type": "button",
        "label": "⬅️ 上一个",
        "variant": "secondary"
    },
    {
        "id": "next_btn",
        "type": "button",
        "label": "下一个 ➡️",
        "variant": "secondary"
    },
    {
        "id": "save_btn",
        "type": "button",
        "label": "💾 保存",
        "variant": "primary"
    }
]

# ============ 布局配置 ============
LAYOUT_CONFIG = {
    "type": "tree",
    "children": [
        # 第一行：搜索+ID 和 状态
        {
            "type": "hstack",
            "elem_id": "top_row",
            "children": ["model_id", "annotation_status"]
        },
        
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
        # 操作按钮
        {
            "type": "hstack",
            "elem_id": "button_row",
            "children": ["prev_btn", "save_btn", "next_btn"]
        },
        # 进度
        "progress_box"
    ]
}

# ============ UI配置 ============
UI_CONFIG = {
    "title": "部件标注工具",
    "enable_checkboxes": True,
    "show_user_info": True,
    "show_status": True,
}

# CSS配置
CUSTOM_CSS = """
/* 全局：响应式布局 */
.gradio-app, .gradio-container {
    max-width: 100% !important;
    width: 100% !important;
}

.gradio-container {
    padding-left: 12px !important;
    padding-right: 12px !important;
}

.gradio-container > .gradio-column {
    gap: 8px !important;
    width: 100% !important;
}

/* 顶部行：model_id & 状态 */
#top_row {
    display: flex !important;
    align-items: stretch !important;
    width: 100% !important;
    gap: 12px !important;
}
#top_row > .gradio-column {
    display: flex !important;
    align-items: stretch !important;
}
#top_row .gradio-textbox,
#top_row .gradio-html {
    display: flex !important;
    flex-direction: column !important;
    width: 100% !important;
}
#top_row .gradio-html > div {
    flex: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

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

/* 尺寸与尺度组合块（右栏） */
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

/* 确认弹窗样式 */
#confirm_modal {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    z-index: 9999;
    display: flex !important;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(3px);
    animation: fadeIn 0.15s ease;
}

#confirm_card {
    width: min(400px, 80vw);
    max-height: min(280px, 45vh);
    overflow-y: auto;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.25);
    padding: 28px 24px 24px;
    animation: slideIn 0.2s ease;
}

#confirm_card h2, #confirm_card p {
    font-size: 20px !important;
    margin: 0 0 10px;
    color: #222;
    text-align: center;
    font-weight: 600;
    line-height: 1.3;
}

#confirm_card button,
#confirm_card .gradio-button,
#confirm_card .gradio-button > span {
    font-size: 14px !important;
    font-weight: 600 !important;
    min-height: 48px !important;
    padding: 12px 20px !important;
    border-radius: 8px !important;
    line-height: 1.2 !important;
}

/* 操作按钮行 */
#button_row {
    display: flex !important;
    justify-content: center !important;
    gap: 12px !important;
    flex-wrap: nowrap !important;
    margin-top: 16px !important;
    width: 100% !important;
}
#button_row .gradio-button {
    flex: 0 1 auto !important;
    min-width: 120px !important;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideIn {
    from { transform: translateY(-30px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}

@media (max-width: 600px) {
    #confirm_card {
        width: 92vw;
        max-height: 65vh;
    }
    #confirm_card h2, #confirm_card p { 
        font-size: 14px !important; 
    }
}
"""

