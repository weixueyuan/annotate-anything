"""
基础UI配置 - 所有任务共享
"""

# ============ 基础UI配置 ============
BASE_UI_CONFIG = {
    "title": "标注工具",
    "enable_checkboxes": True,
    "show_user_info": True,
    "show_status": True,
}

# ============ 基础组件定义 ============
BASE_COMPONENTS = [
    # 搜索和当前ID合并框
    {
        "id": "model_id",
        "type": "search",
        "label": "🔍 Model ID（可搜索）",
        "placeholder": "显示当前ID，可输入其他ID，必须按回车键才能搜索",
        "lines": 1,
        "searchable": True,
        "search_field": "model_id"
    },
    # 状态显示
    {
        "id": "annotation_status",
        "type": "html",
        "value": "",
        "data_field": "_computed_status"
    },
    # 进度显示（移到右栏底部）
    {
        "id": "progress_box",
        "type": "textbox",
        "label": "",  # 去掉标签
        "lines": 1,
        "interactive": False,
        "elem_id": "progress_box"  # 添加elem_id以便CSS定位
    },
    # 导航和保存按钮
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

# ============ 基础CSS样式 ============
BASE_CSS = """
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