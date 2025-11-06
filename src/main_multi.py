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
from src.component_factory import ComponentFactory
from src.routes import ROUTES, DEFAULT_PORT
from src.ui_configs import base_config
from src.auth_handler import AuthHandler


class TaskManager:
    """任务管理器"""
    
    # HTML 模板
    STATUS_ANNOTATED_HTML = '<div style="height: 100%; min-height: 56px; background-color: #d4edda; border: 2px solid #c3e6cb; padding: 8px; font-size: 14px; text-align: center; font-weight: 600; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-sizing: border-box; color: #155724;">✅ 已标注</div>'
    STATUS_NOT_ANNOTATED_HTML = '<div style="height: 100%; min-height: 56px; background-color: #f8d7da; border: 2px solid #f5c6cb; padding: 8px; font-size: 14px; text-align: center; font-weight: 600; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-sizing: border-box; color: #721c24;">❌ 未标注</div>'
    USER_INFO_HTML_TEMPLATE = '<div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:12px;border-radius:8px;text-align:center;">👤 用户：{user_uid} | 📊 可见：{visible} | 🔒 其他：{others}</div>'

    def __init__(self, task_config, user_uid="default_user", debug=False, export_dir="exports", default_allowed_path="/mnt"):
        self.task_config = task_config
        self.user_uid = user_uid
        self.task_name = task_config['task']
        self.debug = debug
        self.export_dir = export_dir
        self.default_allowed_path = default_allowed_path
        
        task_config_module = importlib.import_module(f"src.ui_configs.{self.task_name}_config")

        self.ui_config = base_config.BASE_UI_CONFIG.copy()
        self.ui_config.update(getattr(task_config_module, 'UI_CONFIG', {}))

        task_components = getattr(task_config_module, 'COMPONENTS', [])
        self.components_config = base_config.BASE_COMPONENTS + task_components

        task_css = getattr(task_config_module, 'CUSTOM_CSS', '')
        self.custom_css = base_config.BASE_CSS + task_css
        
        self.task_info = getattr(task_config_module, 'TASK_INFO', {})
        task_layout_config = getattr(task_config_module, 'LAYOUT_CONFIG', {})
        
        # 修复布局合并逻辑
        # 基础布局的子元素
        base_children = [
            {"type": "hstack", "elem_id": "top_row", "children": ["model_id", "annotation_status"]},
            # 占位符，将被任务布局替换
            "task_layout_placeholder",
            {"type": "hstack", "elem_id": "button_row", "children": ["prev_btn", "next_btn", "save_btn"]},
        ]

        # 将任务特定的布局结构插入到基础布局的占位符中
        final_children = []
        for child in base_children:
            if child == "task_layout_placeholder":
                # 插入整个任务布局对象，而不是只插入其子元素
                # 这样可以保留任务布局的根容器（例如 hstack）
                if task_layout_config:
                    final_children.append(task_layout_config)
            else:
                final_children.append(child)

        self.layout_config = {
            "type": "tree",
            "children": final_children
        }
        
        self.field_configs = [
            comp for comp in self.components_config 
            if comp.get('type') not in ['button', 'html'] and comp.get('id') not in ['model_id', 'annotation_status']
        ]
        
        self.db_path = f"databases/{self.task_name}.db"
        
        self.field_processor = FieldProcessor()
        self._load_data()
        
        self.components = {}
        self.factory = None
    
    def _load_data(self):
        if self.debug:
            jsonl_file = 'database_jsonl/test.jsonl'
            if not os.path.exists(jsonl_file):
                os.makedirs(os.path.dirname(jsonl_file), exist_ok=True)
                with open(jsonl_file, 'w', encoding='utf-8') as f:
                    f.write("")
            self.data_handler = JSONLHandler(jsonl_file)
            self.data_source = 'jsonl'
        else:
            self.data_handler = DatabaseHandler(self.db_path)
            self.data_source = 'database'

        if not self.data_handler:
            self.all_data = {}
            self.visible_keys = []
            return

        self.all_data = self.data_handler.load_data()
        self._refresh_visible_keys()
        
        print(f"✓ 加载完成: {len(self.all_data)} 条记录, {len(self.visible_keys)} 条可见")
    
    def _refresh_visible_keys(self):
        self.visible_keys = [
            key for key, value in self.all_data.items()
            if not self.data_handler.parse_item(value).get('uid') or self.data_handler.parse_item(value).get('uid') == self.user_uid
        ]
    
    def build_interface(self):
        if not self.data_handler:
            with gr.Blocks() as demo:
                gr.Markdown(f"# ⚠️ 数据库未初始化\n请先运行: `python -m src.importers.generic_importer --task {self.task_name}`")
            return demo
        
        self.factory = ComponentFactory()
        
        with gr.Blocks(title=self.ui_config['title'], css=self.custom_css) as demo:
            gr.Markdown(f"# {self.ui_config['title']}")
            
            if self.ui_config.get('show_user_info'):
                other_count = len(self.all_data) - len(self.visible_keys)
                self.components['user_info_html'] = gr.HTML(self._render_user_info(len(self.visible_keys), other_count))

            self.components['current_index'] = gr.State(value=0)
            self.components['nav_direction'] = gr.State(value="next")
            self.components['original_dimensions'] = gr.State(value="")

            self.dimension_field_name = next((
                comp.get('target_field') for comp in self.components_config
                if comp.get('type') == 'slider' and comp.get('target_field')
            ), None)

            self.factory.build_layout(self.components_config, self.layout_config)
            self.components.update(self.factory.get_all_components())
            
            if not self.debug and self.data_source == 'database':
                with gr.Row(elem_id="export_row"):
                    self.components['export_btn'] = gr.Button("📤 导出为JSONL", variant="secondary")
                    self.components['export_status'] = gr.Textbox(label="导出状态", interactive=False, visible=False)
            
            with gr.Column(visible=False, elem_id="confirm_modal") as confirm_modal:
                with gr.Column(elem_id="confirm_card"):
                    gr.HTML("<h2>⚠️ 有未保存的修改</h2><p>是否继续？</p>")
                    with gr.Row():
                        self.components['save_and_continue'] = gr.Button("💾 保存并继续", variant="primary", size="sm")
                        self.components['cancel_nav'] = gr.Button("❌ 取消", variant="secondary", size="sm")
                    self.components['skip_changes'] = gr.Button("⚠️ 放弃更改", variant="stop", size="sm")
            
            self.components['confirm_modal'] = confirm_modal
            
            self._bind_events(demo)
            
        return demo
    
    def _bind_events(self, demo):
        self.field_components = []
        self.checkbox_components = []
        for comp_config in self.components_config:
            comp_id = comp_config['id']
            component = self.components.get(comp_id)
            if component and comp_config.get('type') not in ['button', 'html', 'state', 'slider']:
                if comp_config.get('has_checkbox'):
                    if isinstance(component, (list, tuple)):
                        self.checkbox_components.append(component[0])
                        self.field_components.append(component[1])
                    else:
                        # Fallback for safety, though factory should create tuples
                        chk = self.factory.get_checkbox(comp_id)
                        if chk: self.checkbox_components.append(chk)
                        self.field_components.append(component)
                else:
                    self.field_components.append(component)

        model_id_display = self.components.get('model_id')
        scale_slider = self.components.get('scale_slider')
        prev_btn = self.components.get('prev_btn')
        next_btn = self.components.get('next_btn')
        save_btn = self.components.get('save_btn')
        
        _, self.load_outputs = self._get_dynamic_outputs()
        
        demo.load(fn=self.load_data, inputs=[self.components['current_index']], outputs=self.load_outputs)
        
        if self.dimension_field_name and scale_slider:
            target_comp = self.components.get(self.dimension_field_name)
            if target_comp:
                scale_slider.change(
                    fn=self.scale_dimensions,
                    inputs=[self.components['original_dimensions'], scale_slider],
                    outputs=[target_comp]
                )
        
        if model_id_display:
            search_outputs = [self.components['current_index']] + self.load_outputs
            model_id_display.submit(
                fn=self.search_and_load,
                inputs=[model_id_display],
                outputs=search_outputs
            )
        
        save_inputs = [self.components['current_index'], model_id_display] + self.field_components + self.checkbox_components
        save_btn.click(fn=self.save_data, inputs=save_inputs, outputs=self.load_outputs)
        
        nav_inputs = [self.components['current_index'], model_id_display] + self.field_components + self.checkbox_components
        nav_outputs = [self.components['current_index']] + self.load_outputs + [self.components['confirm_modal'], self.components['nav_direction']]
        
        prev_btn.click(fn=self.check_and_nav_prev, inputs=nav_inputs, outputs=nav_outputs)
        next_btn.click(fn=self.check_and_nav_next, inputs=nav_inputs, outputs=nav_outputs)
        
        if 'export_btn' in self.components:
            self.components['export_btn'].click(fn=self.export_to_jsonl, outputs=[self.components['export_status']])
        
        save_and_continue_inputs = [self.components['current_index'], model_id_display, self.components['nav_direction']] + self.field_components + self.checkbox_components
        save_and_continue_outputs = [self.components['current_index']] + self.load_outputs + [self.components['confirm_modal']]
        self.components['save_and_continue'].click(fn=self.save_and_continue_nav, inputs=save_and_continue_inputs, outputs=save_and_continue_outputs)
        
        skip_and_continue_outputs = [self.components['current_index']] + self.load_outputs + [self.components['confirm_modal']]
        self.components['skip_changes'].click(fn=self.skip_and_continue_nav, inputs=[self.components['current_index'], model_id_display, self.components['nav_direction']], outputs=skip_and_continue_outputs)
        
        self.components['cancel_nav'].click(fn=lambda: gr.update(visible=False), outputs=[self.components['confirm_modal']])

    def _get_dynamic_outputs(self, item_attrs=None, index=None, model_id=None):
        output_values = []
        output_components = []
        original_dims_value = ""

        # 预先计算一些常用值，避免重复计算
        progress_value = f"{index + 1} / {len(self.visible_keys)}" if index is not None and self.visible_keys else ""
        status_value = self._render_status(item_attrs.get('annotated', False)) if item_attrs else ""

        for comp_config in self.components_config:
            comp_id = comp_config['id']
            comp_type = comp_config['type']
            data_field = comp_config.get('data_field', comp_id)
            
            # 跳过不参与数据加载的组件
            if comp_type in ['button', 'state']:
                continue

            component = self.components.get(comp_id)
            if not component:
                continue

            # --- 值和组件的生成 ---
            if comp_config.get('has_checkbox'):
                # 对于带复选框的字段
                checkbox_comp = self.factory.get_checkbox(comp_id)
                text_comp = component[1] if isinstance(component, (list, tuple)) else component
                
                if item_attrs:
                    field_value = item_attrs.get(data_field, '')
                    processed_value = self.field_processor.process_load(comp_config, field_value)
                    checkbox_value = item_attrs.get(f"chk_{data_field}", False)
                    output_values.extend([checkbox_value, processed_value])
                else:
                    output_values.extend([False, ""])
                
                if checkbox_comp: output_components.append(checkbox_comp)
                if text_comp: output_components.append(text_comp)

                if item_attrs and self.dimension_field_name and data_field == self.dimension_field_name:
                    original_dims_value = item_attrs.get(self.dimension_field_name, '')

            else:
                # 对于普通字段 - 使用预计算的值
                value = None
                if item_attrs:
                    if data_field == 'model_id':
                        value = model_id
                    elif data_field == '_computed_status':
                        value = status_value  # 使用预计算的状态值
                    elif comp_id == 'progress_box':
                        value = progress_value  # 使用预计算的进度值
                    elif comp_type == 'image':
                        img_path = item_attrs.get(data_field)
                        # 优化：只在图片路径存在时才检查文件是否存在
                        value = img_path if img_path and (not img_path.startswith('/') or os.path.exists(img_path)) else None
                    elif comp_id == 'scale_slider':
                        value = 1.0
                    else:
                        value = item_attrs.get(data_field, '')
                else:
                    if comp_id == 'scale_slider': value = 1.0
                    else: value = ""
                
                output_values.append(value)
                output_components.append(component)

        # 总是添加 original_dimensions state
        output_values.append(original_dims_value)
        output_components.append(self.components['original_dimensions'])
            
        return output_values, output_components

    def load_data(self, index):
        if not self.visible_keys or not (0 <= index < len(self.visible_keys)):
            values, _ = self._get_dynamic_outputs()
            return values

        model_id = self.visible_keys[index]
        item = self.all_data.get(model_id)
        if not item:
            values, _ = self._get_dynamic_outputs()
            return values

        attrs = self.data_handler.parse_item(item)
        if not attrs.get('uid') and hasattr(self.data_handler, "assign_to_user"):
            self.data_handler.assign_to_user(model_id, self.user_uid)
            self.all_data = self.data_handler.load_data()
            self._refresh_visible_keys()
            item = self.all_data.get(model_id)
            attrs = self.data_handler.parse_item(item)
        
        values, _ = self._get_dynamic_outputs(attrs, index, model_id)
        return values
    
    def scale_dimensions(self, original_dims, scale_value):
        if not original_dims or not original_dims.strip(): return ""
        try:
            parts = original_dims.replace('*', ' ').split()
            numbers = [float(p.strip()) for p in parts if p.strip()]
            if not numbers: return original_dims
            scaled_numbers = [n * scale_value for n in numbers]
            return ' * '.join([f"{n:.2f}" if n >= 0.01 else f"{n:.4f}" for n in scaled_numbers])
        except Exception as e:
            print(f"⚠️  尺度计算错误: {e}")
            return original_dims
    
    def _resolve_model(self, index, model_id):
        if model_id and model_id in self.visible_keys:
            return self.visible_keys.index(model_id), model_id
        if 0 <= index < len(self.visible_keys):
            return index, self.visible_keys[index]
        return index, None
    
    def save_data(self, index, model_id, *values):
        resolved_index, resolved_model = self._resolve_model(index, model_id)
        if resolved_model is None:
            return self.load_data(resolved_index)
        
        num_fields = len(self.field_components)
        field_values = values[:num_fields]
        checkbox_values = values[num_fields:]
        
        attributes = {}
        has_error = False
        
        chk_idx = 0
        for i, field_comp in enumerate(self.field_components):
            field_id = field_comp.elem_id
            field_config = next((c for c in self.components_config if c['id'] == field_id), None)
            if not field_config: continue

            value = field_values[i]
            attributes[field_id] = self.field_processor.process_save(field_config, value)
            
            if field_config.get('has_checkbox'):
                if chk_idx < len(checkbox_values):
                    chk_value = checkbox_values[chk_idx]
                    attributes[f"chk_{field_id}"] = chk_value
                    if chk_value: has_error = True
                    chk_idx += 1
        
        score = 0 if has_error else 1
        
        result = self.data_handler.save_item(resolved_model, attributes, score=score, uid=self.user_uid)
        
        if isinstance(result, dict) and not result.get("success", True):
            print(f"❌ 保存失败: {result.get('message', '未知错误')}")
        else:
            print(f"✅ 保存: {resolved_model}, score={score}, uid={self.user_uid}")
        
        self.all_data = self.data_handler.load_data()
        self._refresh_visible_keys()
        
        return self.load_data(resolved_index)
    
    def search_and_load(self, search_value):
        search_value = search_value.strip() if search_value else ""
        if search_value in self.visible_keys:
            new_index = self.visible_keys.index(search_value)
            print(f"🔍 搜索成功: {search_value} (索引 {new_index})")
            return [new_index] + self.load_data(new_index)
        else:
            print(f"⚠️  未找到: {search_value}")
            current_index = self.components['current_index'].value
            return [current_index] + self.load_data(current_index)
    
    def has_real_changes(self, index, model_id, *field_values_and_checkboxes):
        if not self.visible_keys or not (0 <= index < len(self.visible_keys)): return False
        
        current_model_id = self.visible_keys[index] if not model_id or model_id not in self.all_data else model_id
        if current_model_id not in self.all_data: return False
        
        attrs = self.data_handler.parse_item(self.all_data[current_model_id])
        
        num_fields = len(self.field_components)
        current_field_values = list(field_values_and_checkboxes[:num_fields])
        current_checkbox_values = list(field_values_and_checkboxes[num_fields:])
        
        chk_idx = 0
        for i, field_comp in enumerate(self.field_components):
            field_id = field_comp.elem_id
            field_config = next((c for c in self.components_config if c['id'] == field_id), None)
            # 跳过不需要比较的组件：model_id、progress_box、annotation_status等
            if not field_config or field_id in ['model_id', 'progress_box', 'annotation_status']: continue
            # 跳过只读组件
            if field_config.get('interactive') is False: continue

            original_value = self.field_processor.process_load(field_config, attrs.get(field_id, '')) or ""
            current_value = current_field_values[i] or ""
            
            original_str = str(original_value).strip()
            current_str = str(current_value).strip()

            if '*' in original_str or '*' in current_str:
                if original_str.replace(' ', '') != current_str.replace(' ', ''): return True
            elif original_str != current_str: return True
            
            if field_config.get('has_checkbox') and chk_idx < len(current_checkbox_values):
                if attrs.get(f"chk_{field_id}", False) != current_checkbox_values[chk_idx]: return True
                chk_idx += 1
        
        return False
    
    def _check_and_nav(self, index, model_id, direction, *field_values_and_checkboxes):
        if self.has_real_changes(index, model_id, *field_values_and_checkboxes):
            num_load_outputs = len(self.load_outputs)
            updates = [gr.update()] * (1 + num_load_outputs)
            return updates + [gr.update(visible=True), gr.update(value=direction)]
        else:
            new_index, _ = self._go_direction(index, model_id, direction)
            new_data = self.load_data(new_index)
            return [new_index] + new_data + [gr.update(visible=False), gr.update()]

    def check_and_nav_prev(self, index, model_id, *field_values_and_checkboxes):
        return self._check_and_nav(index, model_id, "prev", *field_values_and_checkboxes)
    
    def check_and_nav_next(self, index, model_id, *field_values_and_checkboxes):
        return self._check_and_nav(index, model_id, "next", *field_values_and_checkboxes)
    
    def _go_direction(self, index, model_id, direction):
        resolved_index, _ = self._resolve_model(index, model_id)
        if direction == "prev":
            new_index = max(0, resolved_index - 1)
        else:
            new_index = min(len(self.visible_keys) - 1, resolved_index + 1)
        
        new_model_id = self.visible_keys[new_index] if new_index < len(self.visible_keys) else ""
        return new_index, new_model_id
    
    def save_and_continue_nav(self, index, model_id, direction, *field_values_and_checkboxes):
        self.save_data(index, model_id, *field_values_and_checkboxes)
        new_index, _ = self._go_direction(index, model_id, direction)
        new_data = self.load_data(new_index)
        return [new_index] + new_data + [gr.update(visible=False)]
    
    def skip_and_continue_nav(self, index, model_id, direction):
        new_index, _ = self._go_direction(index, model_id, direction)
        new_data = self.load_data(new_index)
        return [new_index] + new_data + [gr.update(visible=False)]
    
    def export_to_jsonl(self):
        try:
            filepath = self.data_handler.export_to_jsonl(output_dir=self.export_dir)
            return gr.update(value=f"✅ 导出成功: {os.path.basename(filepath)}", visible=True)
        except Exception as e:
            print(f"❌ 导出错误: {e}")
            return gr.update(value=f"❌ 导出失败: {e}", visible=True)
    
    def _render_status(self, annotated):
        return self.STATUS_ANNOTATED_HTML if annotated else self.STATUS_NOT_ANNOTATED_HTML
    
    def _render_user_info(self, visible, others):
        return self.USER_INFO_HTML_TEMPLATE.format(user_uid=self.user_uid, visible=visible, others=others)
    
    def get_allowed_paths(self):
        if not self.all_data: return [self.default_allowed_path]
        
        first_item = list(self.all_data.values())[0]
        attrs = self.data_handler.parse_item(first_item)
        image_url = attrs.get('image_url', '')
        
        if image_url and image_url.startswith('/'):
            parts = image_url.split('/')
            if len(parts) > 1 and parts[1]:
                return [f"/{parts[1]}"]
        
        return [self.default_allowed_path]


def create_login_interface(auth_handler, manager, dev_user=None):
    with gr.Blocks(title=manager.ui_config['title'], css=manager.custom_css) as unified_demo:
        user_state = gr.State(value=manager.user_uid)

        with gr.Column(visible=(dev_user is None), elem_id="login_panel") as login_panel:
            gr.Markdown(f"# 🔐 {manager.ui_config['title']}\n## 登录")
            login_username = gr.Textbox(label="用户名", placeholder="输入用户名")
            login_password = gr.Textbox(label="密码", type="password", placeholder="输入密码")
            login_btn = gr.Button("登录", variant="primary", size="lg")
            login_status = gr.Textbox(label="状态", interactive=False, visible=False)
        
        with gr.Column(visible=(dev_user is not None), elem_id="annotation_panel") as annotation_panel:
            manager.build_interface()
        
        def do_login(username, password):
            if not username or not password:
                return gr.update(value="请输入用户名和密码", visible=True), gr.update(visible=True), gr.update(visible=False), username
            
            result = auth_handler.login(username, password)
            if result["success"]:
                username_value = result["user"]["username"]
                manager.user_uid = username_value
                manager._refresh_visible_keys()
                return gr.update(value="登录成功", visible=False), gr.update(visible=False), gr.update(visible=True), username_value
            else:
                return gr.update(value=result["message"], visible=True), gr.update(visible=True), gr.update(visible=False), ""

        def load_user_data(user):
            if user and user != "pending_login":
                print(f"🔄 为用户 '{user}' 加载数据...")
                return [0] + manager.load_data(0)
            return [-1] + manager.load_data(-1)

        def update_user_info_display():
            other_count = len(manager.all_data) - len(manager.visible_keys)
            return manager._render_user_info(len(manager.visible_keys), other_count)

        login_outputs = [login_status, login_panel, annotation_panel, user_state]
        user_info_html_component = manager.components.get('user_info_html')

        click_event = login_btn.click(fn=do_login, inputs=[login_username, login_password], outputs=login_outputs)

        data_load_outputs = [manager.components['current_index']] + manager.load_outputs
        data_load_event = click_event.then(fn=load_user_data, inputs=[user_state], outputs=data_load_outputs)
        
        if user_info_html_component:
            data_load_event.then(fn=update_user_info_display, outputs=[user_info_html_component])
    
    return unified_demo


def main():
    parser = argparse.ArgumentParser(description='标注工具 - 支持多任务')
    parser.add_argument('--port', type=int, default=None, help='端口')
    parser.add_argument('--task', type=str, default=None, help='任务名称')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug模式')
    parser.add_argument('--dev', action='store_true', help='开发模式（跳过登录）')
    parser.add_argument('--uid', type=str, default='dev_user', help='开发模式用户ID')
    parser.add_argument('--list-tasks', action='store_true', help='列出所有任务')
    
    args = parser.parse_args()
    
    if args.list_tasks:
        print("\n📋 可用任务列表:")
        for route in ROUTES:
            print(f"  - {route['task']}: {route['description']} (端口: {route['port']})")
        return
    
    task_config = next((r for r in ROUTES if r['task'] == args.task), ROUTES[0])
    if not args.task:
        print(f"💡 未指定任务，使用默认任务: {task_config['task']}")
    
    port = args.port or task_config.get('port', DEFAULT_PORT)
    user_uid = args.uid if args.dev else "pending_login"
    dev_user = args.uid if args.dev else None

    manager = TaskManager(task_config, user_uid, debug=args.debug)

    if not manager.data_handler and not args.debug:
        with gr.Blocks() as error_demo:
            gr.Markdown(f"# ⚠️ 数据库未初始化\n请先运行: `python -m src.importers.generic_importer --task {task_config['task']}`")
        error_demo.launch(server_port=port, server_name="0.0.0.0")
        return
    
    print(f"\n{'='*60}")
    print(f"🚀 {'开发模式' if args.dev else '物体属性标注工具'}")
    print(f"任务: {task_config['task']}, 用户: {user_uid}, 端口: {port}, 模式: {'Debug' if args.debug else '正常'}")
    print(f"{'='*60}\n")

    auth_handler = AuthHandler()
    demo = create_login_interface(auth_handler, manager, dev_user=dev_user)
    
    allowed_paths = manager.get_allowed_paths()
    
    demo.launch(server_port=port, server_name="0.0.0.0", allowed_paths=allowed_paths, show_api=False)


if __name__ == "__main__":
    main()
