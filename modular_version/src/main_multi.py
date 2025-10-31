#!/usr/bin/env python
"""
多任务主程序

目前只有一个任务（annotation），但架构支持以后轻松添加新任务
"""

import os
import sys
import importlib
import argparse
import gradio as gr
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.db_handler import DatabaseHandler
from src.jsonl_handler import JSONLHandler
from src.field_processor import FieldProcessor
from routes import ROUTES, DEFAULT_PORT


class TaskManager:
    """任务管理器"""
    
    def __init__(self, task_config, user_uid="default_user"):
        self.task_config = task_config
        self.user_uid = user_uid
        self.task_name = task_config['task']
        
        # 加载UI配置
        config_module = importlib.import_module(f"ui_configs.{self.task_name}_config")
        self.field_configs = config_module.FIELD_CONFIG
        self.ui_config = config_module.UI_CONFIG
        self.path_config = config_module.PATH_CONFIG
        self.task_info = config_module.TASK_INFO
        self.custom_css = getattr(config_module, 'CUSTOM_CSS', '')
        
        # 数据库路径
        self.db_path = f"databases/{self.task_name}.db"
        
        # 初始化
        self.field_processor = FieldProcessor()
        self._load_data()
    
    def _load_data(self):
        """加载数据（支持数据库模式和 JSONL 模式）"""
        # 从配置中获取 JSONL 文件路径（一个配置对应一个 JSONL 文件）
        jsonl_file = self.path_config.get('jsonl_file')
        
        # 模式选择：JSONL 优先，数据库次之
        if jsonl_file and os.path.exists(jsonl_file):
            # JSONL 模式（直接读取配置文件指定的 JSONL 文件）
            print(f"📄 JSONL 模式: {jsonl_file}")
            self.data_handler = JSONLHandler(jsonl_file)
            self.data_source = 'jsonl'
        elif jsonl_file:
            # 配置了 JSONL 文件但不存在
            print(f"⚠️  配置的 JSONL 文件不存在: {jsonl_file}")
            print(f"   尝试使用数据库模式...")
            if os.path.exists(self.db_path):
                print(f"🗄️  数据库模式: {self.db_path}")
                self.data_handler = DatabaseHandler(self.db_path)
                self.data_source = 'database'
            else:
                print(f"❌ 未找到数据源")
                print(f"   - JSONL: {jsonl_file} (不存在)")
                print(f"   - 数据库: {self.db_path} (不存在)")
                self.data_handler = None
                self.all_data = {}
                self.visible_keys = []
                return
        elif os.path.exists(self.db_path):
            # 未配置 JSONL 文件，使用数据库模式
            print(f"🗄️  数据库模式: {self.db_path}")
            self.data_handler = DatabaseHandler(self.db_path)
            self.data_source = 'database'
        else:
            # 无数据源
            print(f"⚠️  未找到数据源")
            if jsonl_file:
                print(f"   - JSONL: {jsonl_file} (不存在)")
            else:
                print(f"   - JSONL: 未配置")
            print(f"   - 数据库: {self.db_path} (不存在)")
            print(f"   请在 PATH_CONFIG 中配置 'jsonl_file' 或运行: python tools/import_to_db.py")
            self.data_handler = None
            self.all_data = {}
            self.visible_keys = []
            return
        
        # 加载所有数据
        self.all_data = self.data_handler.load_data()
        
        # 过滤可见数据
        self.visible_keys = []
        for key, value in self.all_data.items():
            attrs = self.data_handler.parse_item(value)
            item_uid = attrs.get('uid', '')
            if not item_uid or item_uid == self.user_uid:
                self.visible_keys.append(key)
        
        print(f"✓ 加载完成")
        print(f"  总数: {len(self.all_data)}, 可见: {len(self.visible_keys)}")
    
    def build_interface(self):
        """构建界面"""
        if not self.data_handler:
            with gr.Blocks() as demo:
                gr.Markdown(f"# ⚠️ 数据库未初始化\n运行: `python tools/import_to_db.py`")
            return demo
        
        with gr.Blocks(title=self.ui_config['title'], css=self.custom_css) as demo:
            gr.Markdown(f"# {self.ui_config['title']}")
            
            # 用户信息
            if self.ui_config.get('show_user_info'):
                other_count = len(self.all_data) - len(self.visible_keys)
                _ = gr.HTML(self._render_user_info(len(self.visible_keys), other_count))
            
            current_index = gr.State(value=0)
            nav_direction = gr.State(value="next")
            
            # Model ID 和状态框（单独一行）
            with gr.Row(equal_height=True, elem_id="search_row"):
                model_id_display = gr.Textbox(label="Model ID", interactive=False, scale=3)
                status_box = gr.HTML(value="") if self.ui_config.get('show_status') else None
            
            # GIF 和属性字段（分两列）
            with gr.Row(elem_id="main_content_row"):
                # 左：GIF
                with gr.Column(scale=1, elem_id="gif_container"):
                    gif_display = gr.Image(label="物体可视化", type="filepath", height=580, container=True, show_download_button=False)
                
                # 右：字段
                with gr.Column(scale=1, elem_id="info_column"):
                    # 字段组件
                    field_components = []
                    checkbox_components = []
                    
                    for field in self.field_configs:
                        with gr.Column():
                            if field.get('has_checkbox') and self.ui_config.get('enable_checkboxes'):
                                chk = gr.Checkbox(
                                    label=f"{self.ui_config.get('checkbox_label', '✗')} {field['label']}", 
                                    value=False, container=False
                                )
                                checkbox_components.append(chk)
                            
                            comp = gr.Textbox(
                                label="",
                                lines=field.get('lines', 1),
                                placeholder=field.get('placeholder', ''),
                                show_label=False
                            )
                            field_components.append(comp)
            
            # 按钮和进度（单独在下面）
            with gr.Row():
                prev_btn = gr.Button("⬅️ 上一个", size="lg")
                save_btn = gr.Button("💾 保存", variant="primary", size="lg")
                next_btn = gr.Button("➡️ 下一个", size="lg")
            
            progress = gr.Textbox(label="进度", interactive=False)
            
            # 确认弹窗
            with gr.Column(visible=False, elem_id="confirm_modal") as confirm_modal:
                with gr.Column(elem_id="confirm_card"):
                    gr.HTML("<h2>⚠️ 有未保存的修改</h2><p>是否继续？</p>")
                    with gr.Row():
                        save_and_continue = gr.Button("💾 保存并继续", variant="primary", size="sm")
                        cancel_nav = gr.Button("❌ 取消", variant="secondary", size="sm")
                    skip_changes = gr.Button("⚠️ 放弃更改", variant="stop", size="sm")
            
            # 事件处理
            def load_data(index):
                if not self.visible_keys or index >= len(self.visible_keys):
                    empty_count = 2 + len(field_components) + len(checkbox_components) + (1 if status_box else 0) + 1
                    return [""] * empty_count
                
                model_id = self.visible_keys[index]
                item = self.all_data[model_id]
                attrs = self.data_handler.parse_item(item)
                
                # 直接使用 image_url（数据源已提供：数据库导入时生成，JSONL读取时生成）
                gif_path = attrs.get('image_url', None)
                
                # 检查文件是否存在
                if gif_path and not os.path.exists(gif_path):
                    gif_path = None
                
                field_values = []
                checkbox_values = []
                for field in self.field_configs:
                    value = attrs.get(field['key'], '')
                    field_values.append(self.field_processor.process_load(field, value))
                    
                    if field.get('has_checkbox'):
                        checkbox_values.append(attrs.get(f"chk_{field['key']}", False))
                
                prog = f"{index + 1} / {len(self.visible_keys)}"
                
                result = [gif_path, model_id] + field_values + checkbox_values
                if status_box:
                    status_html = self._render_status(attrs.get('annotated', False))
                    result.append(status_html)
                result.append(prog)
                
                return result
            
            def _resolve_model(index, model_id):
                """根据索引和model_id解析当前记录"""
                resolved_model = None
                resolved_index = index
                if model_id and model_id in self.visible_keys:
                    resolved_model = model_id
                    resolved_index = self.visible_keys.index(model_id)
                elif 0 <= index < len(self.visible_keys):
                    resolved_model = self.visible_keys[index]
                return resolved_index, resolved_model

            def save_data(index, model_id, *values):
                resolved_index, resolved_model = _resolve_model(index, model_id)
                if resolved_model is None:
                    return load_data(resolved_index)
                
                num_fields = len(self.field_configs)
                field_values = values[:num_fields]
                checkbox_values = values[num_fields:]
                
                save_dict = {}
                checkbox_idx = 0
                has_error = False  # 检查是否有任何勾选框被选中
                
                for idx, field in enumerate(self.field_configs):
                    key = field['key']
                    save_dict[key] = self.field_processor.process_save(field, field_values[idx])
                    if field.get('has_checkbox'):
                        chk_value = checkbox_values[checkbox_idx]
                        save_dict[f"chk_{key}"] = chk_value
                        if chk_value:  # 如果有任何勾选框被选中
                            has_error = True
                        checkbox_idx += 1
                
                # 计算 score：如果任意勾选框被选中，score=0；否则score=1
                score = 0 if has_error else 1
                
                # 保存（传递 uid）
                self.data_handler.save_item(resolved_model, save_dict, score=score, uid=self.user_uid)
                print(f"✅ 保存: {resolved_model}, score={score}, uid={self.user_uid}")
                
                # 更新缓存（重新加载以获取最新的文件内容）
                self.all_data = self.data_handler.load_data()
                
                # 重新加载数据
                return load_data(resolved_index)
            
            # 修改检测函数（简化版：直接比较，避免类型转换问题）
            def check_modified(index, model_id, *values):
                """检查当前数据是否被修改"""
                if not self.visible_keys:
                    return False
                
                resolved_index, resolved_model = _resolve_model(index, model_id)
                if resolved_model is None or not (0 <= resolved_index < len(self.visible_keys)):
                    return False
                
                item = self.all_data.get(resolved_model)
                if item is None:
                    # 尝试刷新缓存
                    self.all_data = self.data_handler.load_data()
                    item = self.all_data.get(resolved_model)
                    if item is None:
                        return False
                attrs = self.data_handler.parse_item(item)
                
                num_fields = len(self.field_configs)
                field_values = values[:num_fields]
                checkbox_values = values[num_fields:]
                
                # 构建当前显示的原始值（和 load_data 相同的处理）
                original_values = []
                for field in self.field_configs:
                    value = attrs.get(field['key'], '')
                    original_values.append(self.field_processor.process_load(field, value))
                
                # 比较每个字段（处理 None 和空字符串的等价性）
                for idx in range(num_fields):
                    orig = original_values[idx] if original_values[idx] is not None else ''
                    curr = field_values[idx] if field_values[idx] is not None else ''
                    if str(orig) != str(curr):
                        return True
                
                # 比较勾选框
                checkbox_idx = 0
                for field in self.field_configs:
                    if field.get('has_checkbox'):
                        original_chk = attrs.get(f"chk_{field['key']}", False)
                        current_chk = checkbox_values[checkbox_idx]
                        if original_chk != current_chk:
                            return True
                        checkbox_idx += 1
                
                return False
            
            # 导航函数（带修改检测）
            def navigate_with_check(index, model_id, direction, *values):
                """导航前检查是否有修改"""
                resolved_index, resolved_model = _resolve_model(index, model_id)
                modified = check_modified(resolved_index, resolved_model, *values)
                if modified:
                    # 有修改，显示弹窗
                    return [gr.update(value=resolved_index), gr.update(visible=True), gr.update(value=direction)] + [gr.update()] * len(outputs)
                else:
                    # 无修改，直接跳转并加载数据
                    if direction == "next":
                        new_index = min(len(self.visible_keys) - 1, resolved_index + 1)
                    else:
                        new_index = max(0, resolved_index - 1)
                    
                    load_result = load_data(new_index)
                    return [gr.update(value=new_index), gr.update(visible=False), gr.update()] + load_result
            
            # 保存并继续
            def save_and_nav(index, model_id, direction, *values):
                """保存当前数据并跳转"""
                # 先保存
                _ = save_data(index, model_id, *values)
                
                # 再跳转并加载数据
                resolved_index, _ = _resolve_model(index, model_id)
                if direction == "next":
                    new_index = min(len(self.visible_keys) - 1, resolved_index + 1)
                else:
                    new_index = max(0, resolved_index - 1)
                
                load_result = load_data(new_index)
                return [gr.update(value=new_index), gr.update(visible=False)] + load_result
            
            # 放弃更改并继续
            def skip_and_nav(index, model_id, direction):
                """放弃更改并跳转"""
                resolved_index, _ = _resolve_model(index, model_id)
                if direction == "next":
                    new_index = min(len(self.visible_keys) - 1, resolved_index + 1)
                else:
                    new_index = max(0, resolved_index - 1)
                
                load_result = load_data(new_index)
                return [gr.update(value=new_index), gr.update(visible=False)] + load_result
            
            # 绑定事件
            status_outputs = [status_box] if status_box else []
            outputs = [gif_display, model_id_display] + field_components + checkbox_components + status_outputs + [progress]
            
            # 初始加载
            demo.load(lambda: load_data(0), outputs=outputs)
            
            # 保存按钮
            save_btn.click(
                save_data,
                inputs=[current_index, model_id_display] + field_components + checkbox_components,
                outputs=outputs
            )
            
            # 导航按钮（带修改检测）
            prev_btn.click(
                navigate_with_check,
                inputs=[current_index, model_id_display, gr.State("prev")] + field_components + checkbox_components,
                outputs=[current_index, confirm_modal, nav_direction] + outputs
            )
            
            next_btn.click(
                navigate_with_check,
                inputs=[current_index, model_id_display, gr.State("next")] + field_components + checkbox_components,
                outputs=[current_index, confirm_modal, nav_direction] + outputs
            )
            
            # 确认弹窗按钮
            save_and_continue.click(
                save_and_nav,
                inputs=[current_index, model_id_display, nav_direction] + field_components + checkbox_components,
                outputs=[current_index, confirm_modal] + outputs
            )
            
            skip_changes.click(
                skip_and_nav,
                inputs=[current_index, model_id_display, nav_direction],
                outputs=[current_index, confirm_modal] + outputs
            )
            
            cancel_nav.click(
                lambda: gr.update(visible=False),
                outputs=[confirm_modal]
            )
        
        return demo
    
    def _render_status(self, annotated):
        if annotated:
            return '''<div style="
                height: 100%;
                min-height: 56px;
                background-color: #d4edda;
                border: 2px solid #c3e6cb;
                padding: 8px;
                font-size: 14px;
                text-align: center;
                font-weight: 600;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-sizing: border-box;
                color: #155724;
            ">✅ 已标注</div>'''
        return '''<div style="
            height: 100%;
            min-height: 56px;
            background-color: #f8d7da;
            border: 2px solid #f5c6cb;
            padding: 8px;
            font-size: 14px;
            text-align: center;
            font-weight: 600;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
            color: #721c24;
        ">❌ 未标注</div>'''
    
    def _render_user_info(self, visible, others):
        return f'<div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:12px;border-radius:8px;text-align:center;">👤 用户：{self.user_uid} | 📊 可见：{visible} | 🔒 其他：{others}</div>'


def main():
    parser = argparse.ArgumentParser(description='标注工具')
    parser.add_argument('--uid', type=str, default='default_user', help='用户ID')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='端口')
    args = parser.parse_args()
    
    # 目前只有一个任务
    task_config = ROUTES[0]
    
    print(f"\n{'='*60}")
    print(f"🚀 {task_config['description']}")
    print(f"{'='*60}")
    print(f"用户: {args.uid}")
    print(f"端口: {args.port}")
    print(f"{'='*60}\n")
    
    # 创建任务
    manager = TaskManager(task_config, args.uid)
    demo = manager.build_interface()
    
    # 获取允许访问的路径（GIF文件所在的基础路径）
    allowed_paths = [manager.path_config['base_path']]
    
    # 启动
    demo.launch(server_port=args.port, server_name="0.0.0.0", allowed_paths=allowed_paths)


if __name__ == "__main__":
    main()

