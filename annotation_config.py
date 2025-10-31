"""
物体属性标注任务配置（参考旧版本config.py）
"""

# 任务信息
TASK_INFO = {
    "task_id": "annotation",
    "task_name": "物体属性标注",
    "description": "标注物体的基本属性信息"
}

# 字段配置（从旧版config.py迁移）
FIELD_CONFIG = [
    {
        "key": "category",
        "label": "Category (类别)",
        "type": "textbox",
        "lines": 1,
        "has_checkbox": True,
        "placeholder": "",
        "flex": 1,
        "process": None
    },
    {
        "key": "description",
        "label": "Description (描述)",
        "type": "textbox",
        "lines": 3,
        "has_checkbox": True,
        "placeholder": "",
        "flex": 2
    },
    {
        "key": "material",
        "label": "Material (材质)",
        "type": "textbox",
        "lines": 1,
        "has_checkbox": True,
        "placeholder": "",
        "flex": 1
    },
    {
        "key": "dimensions",
        "label": "Dimensions (尺寸)",
        "type": "textbox",
        "lines": 1,
        "has_checkbox": True,
        "placeholder": "例如: Small, Medium, Large",
        "flex": 1,
        "process": None
    },
    {
        "key": "placement",
        "label": "Placement (放置位置)",
        "type": "textbox",
        "lines": 1,
        "has_checkbox": True,
        "placeholder": "例如: OnTable, OnFloor",
        "flex": 1,
        "process": "array_to_string"
    }
]

# UI配置（从旧版config.py迁移）
UI_CONFIG = {
    "title": "物体属性检查工具",
    "gif_height": None,
    "info_column_height": None,
    "enable_checkboxes": True,
    "checkbox_label": "✗",
    "show_user_info": True,
    "show_status": True,
}

# 路径配置（从旧版config.py迁移）
PATH_CONFIG = {
    "base_path": "/mnt/data/GRScenes-100/instances/renderings",
    "gif_filename_pattern": "{model_id}_fixed.gif",
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

/* 搜索行：模型检索和状态框高度对齐 */
#search_row {
    display: flex !important;
    align-items: stretch !important;
    width: 100% !important;
}
#search_row .gradio-column {
    display: flex !important;
    align-items: stretch !important;
}
#search_row .gradio-textbox {
    display: flex !important;
    flex-direction: column !important;
}
#search_row .gradio-html {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}
#search_row .gradio-html > div {
    flex: 1 !important;
    display: flex !important;
}

/* 主内容行：左右列根据内容自适应高度 */
#main_content_row {
    display: flex !important;
    align-items: flex-start !important;
    gap: 12px !important;
    width: 100% !important;
}
#main_content_row > .gradio-column {
    display: flex !important;
    flex-direction: column !important;
    min-width: 0 !important;
}

/* GIF容器：保持1:1比例，自适应宽度（横向更宽） */
#gif_container {
    aspect-ratio: 1 / 1 !important;
    width: 100% !important;
}
#gif_box, #gif_container .gradio-image {
    aspect-ratio: 1 / 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
#gif_box img, #gif_container .gradio-image img {
    max-width: 100% !important;
    max-height: 100% !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
    margin: auto !important;
}

/* 右侧信息列：自动填充空间 */
#info_column {
    display: flex !important;
    flex-direction: column !important;
    gap: 4px !important;
}
#info_column > .gradio-column {
    display: flex !important;
    flex-direction: column !important;
    width: 100% !important;
}
#info_column > .gradio-row:last-child {
    margin-top: 8px !important;
}
#info_column .gradio-checkbox {
    margin-bottom: 0px !important;
}
#info_column .gradio-textbox {
    flex: 1 1 0 !important;
    min-height: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    width: 100% !important;
}
#info_column .gradio-textbox textarea {
    flex: 1 !important;
    min-height: 0 !important;
}

/* 让description输入框占据2倍空间 */
#info_column > div:nth-child(2) {
    flex: 2 1 0 !important;
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
