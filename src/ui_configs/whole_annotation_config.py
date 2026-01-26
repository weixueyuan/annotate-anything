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
    # 图片显示
    {
        "id": "image_url",           # 直接用数据字段名
        "type": "image",             # type说明这是图片组件
        "label": "GIF预览",
        "interactive": False
    },
    
    # 搜索和当前ID合并框
    {
        "id": "model_id",
        "type": "search",
        "label": "🔍 Model ID（可搜索）",
        "placeholder": "显示当前ID，可输入其他ID，必须按回车键才能搜索",
        "lines": 1,
        "searchable": True,          # 既显示又可搜索
        "search_field": "model_id"
    },
    
    # 状态显示（HTML组件用于显示富文本/样式）
    {
        "id": "annotation_status",
        "type": "html",
        "value": "",
        "data_field": "_computed_status"  # 特殊标记：动态计算
    },
    
    # 属性字段（data_field 默认使用 id）
    {
        "id": "object_name",
        "type": "textbox",
        "label": "物体名称",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
        # data_field 默认为 "object_name"
    },
    {
        "id": "dimension",
        "type": "textbox",
        "label": "尺寸 (X*Y*Z)",
        "lines": 1,
        "has_checkbox": True,
        "checkbox_label": "✗",
        "placeholder": "例如: 0.78*0.41*0.54",
        "data_field": "dimension"  # 明确指定（用于尺度滑块）
    },
    # 尺度滑块（紧跟在dimension下方）
    {
        "id": "scale_slider",
        "type": "slider",
        "label": "🔧 尺度调整",
        "minimum": 0.0,
        "maximum": 10.0,
        "value": 1.0,
        "step": 0.01,
        "target_field": "dimension",  # 关联到dimension字段
        "data_field": "scale_slider"  # 明确指定（用于保存）
    },
    {
        "id": "overall_description",
        "type": "textbox",
        "label": "总体描述",
        "lines": 3,
        # "has_checkbox": True,
        # "checkbox_label": "✗",
        "interactive": False,  # 设置为不可编辑
        # data_field 默认为 "overall_description"
    },
    
    # 进度显示
    {
        "id": "progress_box",
        "type": "textbox",
        "label": "进度",
        "lines": 1,
        "interactive": False
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
# 布局定义：搜索栏在顶部，下面是两栏布局（GIF + 字段）
LAYOUT_CONFIG = {
    "type": "tree",
    "children": [
        # 顶部：搜索+ID 和 状态横向布局
        {
            "type": "hstack",
            "elem_id": "top_row",
            "children": ["model_id", "annotation_status"]
        },
        
        # 中间：两栏布局
        {
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
        },
        
        # 操作按钮（单独一行，在两栏布局下方）
        {
            "type": "hstack",
            "elem_id": "button_row",
            "children": ["prev_btn", "save_btn", "next_btn"]
        }
    ]
}

# ============ UI配置 ============
UI_CONFIG = {
    "title": "整体物体标注工具",
    "enable_checkboxes": True,
    "show_user_info": True,
    "show_status": True,
}

# CSS配置（从旧版config.py迁移）
CUSTOM_CSS = """
/* 全局：响应式布局，消除不必要的空白，页面全宽显示 */
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

/* 操作按钮行：单独一行，在主内容下方，水平居中 */
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

