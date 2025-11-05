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


class TaskManager:
    """任务管理器"""
    
    def __init__(self, task_config, user_uid="default_user", debug=False, export_dir="exports", default_allowed_path="/mnt"):
        self.task_config = task_config
        self.user_uid = user_uid
        self.task_name = task_config['task']
        self.debug = debug
        self.export_dir = export_dir  # 添加导出目录配置，解决硬编码问题
        self.default_allowed_path = default_allowed_path  # 添加默认允许路径，解决硬编码问题
        
        # 加载UI配置（新架构）
        config_module = importlib.import_module(f"src.ui_configs.{self.task_name}_config")
        
        self.components_config = config_module.COMPONENTS
        self.layout_config = config_module.LAYOUT_CONFIG
        self.ui_config = config_module.UI_CONFIG
        self.task_info = config_module.TASK_INFO
        self.custom_css = getattr(config_module, 'CUSTOM_CSS', '')
        
        # 从COMPONENTS中提取字段配置（用于数据处理）
        self.field_configs = []
        for comp in self.components_config:
            if comp.get('has_checkbox') is not None:  # 只要定义了has_checkbox，就认为是字段
                self.field_configs.append({
                    'key': comp['id'],
                    'label': comp['label'],
                    'type': comp['type'],
                    'lines': comp.get('lines', 1),
                    'has_checkbox': comp.get('has_checkbox'),
                    'interactive': comp.get('interactive', True),  # 默认可编辑
                    'placeholder': comp.get('placeholder', ''),
                    'process': comp.get('process')
                })
        
        # 数据库路径
        self.db_path = f"databases/{self.task_name}.db"
        
        # 初始化
        self.field_processor = FieldProcessor()
        self._load_data()
    
    def _load_data(self):
        """加载数据（支持数据库模式和 JSONL debug 模式）"""
        # Debug 模式：使用 test.jsonl
        if self.debug:
            jsonl_file = 'test.jsonl'
            if os.path.exists(jsonl_file):
                print(f"🐛 Debug 模式: {jsonl_file}")
                self.data_handler = JSONLHandler(jsonl_file)
                self.data_source = 'jsonl'
            else:
                print(f"⚠️  Debug 模式：未找到 {jsonl_file}")
                print(f"   创建空的测试文件...")
                # 创建空的 test.jsonl
                with open(jsonl_file, 'w', encoding='utf-8'):
                    pass
                self.data_handler = JSONLHandler(jsonl_file)
                self.data_source = 'jsonl'
                self.all_data = {}
                self.visible_keys = []
                print(f"   ✓ 已创建空的 {jsonl_file}")
                return
        else:
            # 正常模式：使用数据库
            if os.path.exists(self.db_path):
                print(f"🗄️  数据库模式: {self.db_path}")
                self.data_handler = DatabaseHandler(self.db_path)
                self.data_source = 'database'
            else:
                print(f"❌ 未找到数据库: {self.db_path}")
                print(f"   请先导入数据: python -m importers.annotation_importer")
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
        """使用组件工厂构建界面（新架构）"""
        if not self.data_handler:
            with gr.Blocks() as demo:
                gr.Markdown(f"# ⚠️ 数据库未初始化\n运行: `python tools/import_to_db.py`")
            return demo
        
        # 创建组件工厂
        factory = ComponentFactory()
        
        with gr.Blocks(title=self.ui_config['title'], css=self.custom_css) as demo:
            gr.Markdown(f"# {self.ui_config['title']}")
            
            # 用户信息
            if self.ui_config.get('show_user_info'):
                other_count = len(self.all_data) - len(self.visible_keys)
                _ = gr.HTML(self._render_user_info(len(self.visible_keys), other_count))
            
            # State组件
            current_index = gr.State(value=0)
            nav_direction = gr.State(value="next")
            
            # 动态查找尺度滑块的目标字段
            dimension_field_name = None
            for comp_config in self.components_config:
                if comp_config.get('type') == 'slider' and comp_config.get('target_field'):
                    dimension_field_name = comp_config.get('target_field')
                    break
            
            original_dimensions = gr.State(value="")  # 存储原始dimension/dimensions值
            
            # 使用布局配置构建界面（同时创建和渲染组件）
            factory.build_layout(self.components_config, self.layout_config)
            
            # 获取创建的组件
            components = factory.get_all_components()
            
            # 导出按钮（仅在正常模式下显示）
            export_btn = None
            export_status = None
            if not self.debug and self.data_source == 'database':
                with gr.Row():
                    export_btn = gr.Button("📤 导出为JSONL", variant="secondary", size="lg")
                    export_status = gr.Textbox(label="导出状态", interactive=False, visible=False)
            
            # 确认弹窗
            with gr.Column(visible=False, elem_id="confirm_modal") as confirm_modal:
                with gr.Column(elem_id="confirm_card"):
                    gr.HTML("<h2>⚠️ 有未保存的修改</h2><p>是否继续？</p>")
                    with gr.Row():
                        save_and_continue = gr.Button("💾 保存并继续", variant="primary", size="sm")
                        cancel_nav = gr.Button("❌ 取消", variant="secondary", size="sm")
                    skip_changes = gr.Button("⚠️ 放弃更改", variant="stop", size="sm")
            
            # ========== 事件处理函数 ==========
            
            # 提取字段组件和checkbox组件
            field_components = []
            checkbox_components = []
            for field_config in self.field_configs:
                field_id = field_config['key']
                comp = components.get(field_id)
                if isinstance(comp, tuple):
                    # (textbox, checkbox) 元组
                    field_components.append(comp[0])
                    checkbox_components.append(comp[1])
                else:
                    field_components.append(comp)
            
            # 获取其他组件
            gif_display = components.get('image_url')
            model_id_display = components.get('model_id')  # 既用于显示也用于搜索
            status_box = components.get('annotation_status')
            progress = components.get('progress_box')
            scale_slider = components.get('scale_slider')
            prev_btn = components.get('prev_btn')
            next_btn = components.get('next_btn')
            save_btn = components.get('save_btn')
            
            def load_data(index):
                """
                根据组件配置动态加载数据
                通过 data_field 属性将数据库字段映射到UI组件
                """
                if not self.visible_keys or index >= len(self.visible_keys):
                    # 返回空值（数量根据组件配置动态计算，跳过按钮）
                    empty_result = []
                    for comp_config in self.components_config:
                        comp_type = comp_config['type']
                        # 跳过按钮组件（不在输出列表中）
                        if comp_type == 'button':
                            continue
                        
                        if comp_config.get('has_checkbox'):
                            empty_result.append("")  # 字段值
                            empty_result.append(False)  # checkbox值
                        elif comp_config['id'] == 'scale_slider':
                            empty_result.append(1.0)  # 滑块默认值（float）
                        else:
                            empty_result.append("")
                    return empty_result + [""]  # +1 for original_dimensions state
                
                model_id = self.visible_keys[index]
                
                # 直接从all_data获取数据
                item = self.all_data.get(model_id)
                if not item:
                    return empty_result + [""]
                    
                attrs = self.data_handler.parse_item(item)
                
                # 浏览即占有 - 简单直接方式（不使用缓存）
                current_uid = attrs.get('uid', '')
                if not current_uid or current_uid == '':
                    # 数据未分配，立即占有（只设置uid，不触碰其他数据）
                    if hasattr(self.data_handler, "assign_to_user"):
                        self.data_handler.assign_to_user(model_id, self.user_uid)
                        print(f"🔒 占有数据: {model_id} -> {self.user_uid}")
                        # 重新加载全部数据（简单直接）
                        self.all_data = self.data_handler.load_data()
                        # 重新计算可见数据
                        self.visible_keys = []
                        for key, value in self.all_data.items():
                            item_attrs = self.data_handler.parse_item(value)
                            item_uid = item_attrs.get('uid', '')
                            if not item_uid or item_uid == self.user_uid:
                                self.visible_keys.append(key)
                        # 重新获取当前项
                        item = self.all_data.get(model_id)
                        attrs = self.data_handler.parse_item(item)
                
                # 根据配置动态构建返回值（跳过按钮）
                result = []
                original_dims_value = ""  # 用于尺度滑块
                
                for comp_config in self.components_config:
                    comp_id = comp_config['id']
                    comp_type = comp_config['type']
                    
                    # 跳过按钮组件（不在输出列表中）
                    if comp_type == 'button':
                        continue
                    
                    data_field = comp_config.get('data_field', comp_id)  # 默认使用id作为字段名
                    
                    # 处理特殊字段
                    if data_field == 'model_id':
                        result.append(model_id)
                    
                    elif data_field == 'image_url':
                        # 图片路径，检查文件是否存在
                        img_path = attrs.get('image_url', None)
                        if img_path and not os.path.exists(img_path):
                            img_path = None
                        result.append(img_path)
                    
                    elif data_field == '_computed_status':
                        # 动态计算的状态
                        status_html = self._render_status(attrs.get('annotated', False))
                        result.append(status_html)
                    
                    elif comp_id == 'progress_box':
                        # 进度显示
                        prog = f"{index + 1} / {len(self.visible_keys)}"
                        result.append(prog)
                    
                    elif comp_id == 'scale_slider':
                        # 尺度滑块重置为1.0（确保是float类型）
                        result.append(float(1.0))
                    
                    elif comp_config.get('has_checkbox'):
                        # 带checkbox的字段
                        value = attrs.get(data_field, '')
                        # 使用 field_processor 处理字段值
                        field_info = {'key': data_field, 'process': comp_config.get('process')}
                        processed_value = self.field_processor.process_load(field_info, value)
                        result.append(processed_value)
                        
                        # 添加checkbox值
                        checkbox_value = attrs.get(f"chk_{data_field}", False)
                        result.append(checkbox_value)
                        
                        # 保存dimension/dimensions原始值（用于尺度滑块）
                        if dimension_field_name and data_field == dimension_field_name:
                            original_dims_value = attrs.get(dimension_field_name, '')
                    
                    # 处理其他图片字段（part_annotation 有多个图片）
                    elif comp_type == 'image' and data_field not in ['model_id', '_computed_status']:
                        # 其他图片字段（如 image_url_p1, image_url_p2）
                        img_path = attrs.get(data_field, None)
                        if img_path and not os.path.exists(img_path):
                            img_path = None
                        result.append(img_path)
                
                # 添加 original_dimensions state
                result.append(original_dims_value)
                
                return result
            
            def scale_dimensions(original_dims, scale_value):
                """根据尺度滑块值计算缩放后的dimensions"""
                if not original_dims or not original_dims.strip():
                    return ""
                try:
                    parts = original_dims.replace('*', ' ').split()
                    numbers = [float(p.strip()) for p in parts if p.strip()]
                    if not numbers:
                        return original_dims
                    scaled_numbers = [n * scale_value for n in numbers]
                    result = ' * '.join([f"{n:.2f}" if n >= 0.01 else f"{n:.4f}" for n in scaled_numbers])
                    return result
                except Exception as e:
                    print(f"⚠️  尺度计算错误: {e}")
                    return original_dims
            
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
               
               attributes = {}
               has_error = False  # 追踪是否有任何checkbox被选中
               
               for i, field in enumerate(self.field_configs):
                   key = field['key']
                   value = field_values[i]
                   attributes[key] = self.field_processor.process_save(field, value)
                   if field.get('has_checkbox') and i < len(checkbox_values):
                       chk_value = checkbox_values[i]
                       attributes[f"chk_{key}"] = chk_value
                       if chk_value:  # 如果任何checkbox被选中，标记为有错误
                           has_error = True
               
               # 计算score：如果任意一个checkbox被选中，score=0；否则score=1
               score = 0 if has_error else 1
               
               # 直接使用data_handler保存（不使用缓存）
               result = self.data_handler.save_item(
                   resolved_model,
                   attributes,
                   score=score,
                   uid=self.user_uid
               )
               
               # 检查保存结果
               if isinstance(result, dict) and not result.get("success", True):
                   # 保存失败，提供详细错误信息
                   error_type = result.get("error", "UNKNOWN_ERROR")
                   error_msg = result.get("message", "未知错误")
                   print(f"❌ 保存失败 ({error_type}): {error_msg}")
                   
                   # 构建错误状态HTML
                   error_status_html = f'''<div style="
                       background-color: #f8d7da;
                       border: 2px solid #f5c6cb;
                       padding: 8px;
                       font-size: 14px;
                       text-align: center;
                       font-weight: 600;
                       border-radius: 6px;
                       color: #721c24;
                   ">❌ 保存失败: {error_msg}</div>'''
                   
                   # 返回当前数据并显示错误信息
                   result = load_data(resolved_index)
                   # 如果状态框在加载的组件中，则替换状态框内容
                   for i, comp in enumerate(self.components_config):
                       if comp.get('data_field') == '_computed_status':
                           result[i] = error_status_html
                   
                   return result
               else:
                   # 保存成功
                   print(f"✅ 保存: {resolved_model}, score={score}, uid={self.user_uid}")
                   
                   # 重新加载数据（简单直接）
                   self.all_data = self.data_handler.load_data()
                   
                   # 重新计算可见键
                   self.visible_keys = []
                   for key, value in self.all_data.items():
                       attrs = self.data_handler.parse_item(value)
                       item_uid = attrs.get('uid', '')
                       if not item_uid or item_uid == self.user_uid:
                           self.visible_keys.append(key)
                   
                   return load_data(resolved_index)
            
            def go_prev(index, model_id):
                """上一个：只返回新的 model_id"""
                resolved_index, _ = _resolve_model(index, model_id)
                new_index = max(0, resolved_index - 1)
                new_model_id = self.visible_keys[new_index] if new_index < len(self.visible_keys) else ""
                return new_model_id
            
            def go_next(index, model_id):
                """下一个：只返回新的 model_id"""
                resolved_index, _ = _resolve_model(index, model_id)
                new_index = min(len(self.visible_keys) - 1, resolved_index + 1)
                new_model_id = self.visible_keys[new_index] if new_index < len(self.visible_keys) else ""
                return new_model_id
            
            def search_and_load(search_value):
                """
                搜索功能：根据输入的值查找对应的 model_id
                
                Args:
                    search_value: model_id输入框的值
                    
                Returns:
                    更新后的所有组件值
                """
                if not search_value or not search_value.strip():
                    # 空搜索，不做任何操作，保持当前数据
                    return [current_index.value] + load_data(current_index.value)
                
                search_value = search_value.strip()
                
                # 查找 model_id（在 visible_keys 中）
                if search_value in self.visible_keys:
                    # 找到了，跳转到该索引
                    new_index = self.visible_keys.index(search_value)
                    print(f"🔍 搜索成功: {search_value} (索引 {new_index})")
                    return [new_index] + load_data(new_index)
                else:
                    # 未找到，提示用户，保持当前数据
                    print(f"⚠️  未找到: {search_value}")
                    return [current_index.value] + load_data(current_index.value)
            
            def has_real_changes(index, model_id, *field_values_and_checkboxes):
                """检查当前字段值是否与数据库中的原始值不同"""
                if not self.visible_keys or index >= len(self.visible_keys):
                    return False
                
                # 获取数据库中的原始数据
                if model_id and model_id in self.all_data:
                    current_model_id = model_id
                elif index < len(self.visible_keys):
                    current_model_id = self.visible_keys[index]
                else:
                    return False
                
                if current_model_id not in self.all_data:
                    return False
                
                item = self.all_data[current_model_id]
                attrs = self.data_handler.parse_item(item)
                
                # 分离字段值和checkbox值
                num_fields = len(self.field_configs)
                current_field_values = list(field_values_and_checkboxes[:num_fields])
                current_checkbox_values = list(field_values_and_checkboxes[num_fields:])
                
                checkbox_idx = 0
                # 对比每个字段
                for i, field in enumerate(self.field_configs):
                    if i >= len(current_field_values):
                        continue  # 防止索引越界
                    
                    # 对比字段值
                    key = field['key']
                    original_value = attrs.get(key, '')
                    # 使用processor处理原始值，确保与UI显示格式一致
                    processed_value = self.field_processor.process_load(field, original_value)
                    if processed_value is None:
                        processed_value = ""
                        
                    current_value = current_field_values[i]
                    if current_value is None:
                        current_value = ""
                    
                    # 字符串对比（去除首尾空格）
                    if str(processed_value).strip() != str(current_value).strip():
                        print(f"字段 '{key}' 已修改: '{processed_value}' -> '{current_value}'")
                        return True
                    
                    # 对比checkbox值
                    if field.get('has_checkbox') and checkbox_idx < len(current_checkbox_values):
                        original_checkbox = attrs.get(f"chk_{key}", False)
                        current_checkbox = current_checkbox_values[checkbox_idx]
                        if original_checkbox != current_checkbox:
                            print(f"复选框 '{key}' 已修改: {original_checkbox} -> {current_checkbox}")
                            return True
                        checkbox_idx += 1
                
                return False
            
            # ========== 事件绑定 ==========
            
            # 构建 load_outputs（按照COMPONENTS配置顺序，跳过按钮）
            load_outputs = []
            for comp_config in self.components_config:
                comp_id = comp_config['id']
                comp_type = comp_config['type']
                
                # 跳过按钮组件
                if comp_type == 'button':
                    continue
                
                comp = components.get(comp_id)
                if comp:
                    # 如果是元组（textbox + checkbox），展开添加
                    if isinstance(comp, tuple):
                        load_outputs.extend(comp)
                    else:
                        load_outputs.append(comp)
            
            # 添加 original_dimensions state
            load_outputs.append(original_dimensions)
            
            demo.load(fn=load_data, inputs=[current_index], outputs=load_outputs)
            
            # model_id 变化时自动加载数据
            def on_model_id_change(model_id_value):
                """model_id 变化时加载对应的数据"""
                if not model_id_value or model_id_value not in self.visible_keys:
                    return load_data(0)
                new_index = self.visible_keys.index(model_id_value)
                return [new_index] + load_data(new_index)
            
            model_id_change_outputs = [current_index] + load_outputs
            model_id_display.change(
                fn=on_model_id_change,
                inputs=[model_id_display],
                outputs=model_id_change_outputs
            )
            
            # 滑块变化时更新dimension/dimensions字段
            dimensions_idx = None
            if dimension_field_name:
                for i, field in enumerate(self.field_configs):
                    if field['key'] == dimension_field_name:
                        dimensions_idx = i
                        break
            
            if dimensions_idx is not None and scale_slider:
                scale_slider.change(
                    fn=scale_dimensions,
                    inputs=[original_dimensions, scale_slider],
                    outputs=[field_components[dimensions_idx]]
                )
            
            # 搜索功能（按回车触发）- model_id既显示也可搜索
            if model_id_display:
                search_outputs = [current_index] + load_outputs
                model_id_display.submit(
                    fn=search_and_load,
                    inputs=[model_id_display],
                    outputs=search_outputs
                )
            
            # 保存
            save_inputs = [current_index, model_id_display] + field_components + checkbox_components
            save_btn.click(fn=save_data, inputs=save_inputs, outputs=load_outputs)
            
            # 导航检查和跳转
            def check_and_nav(nav_func, direction_value):
                """导航检查：对比当前值与数据库值，如果有差异显示弹窗，否则直接跳转"""
                def wrapper(index, model_id, *field_values_and_checkboxes):
                    # 检查是否有真实的修改（对比数据库值）
                    if has_real_changes(index, model_id, *field_values_and_checkboxes):
                        # 有修改，显示弹窗，记录方向
                        return gr.update(), gr.update(visible=True), gr.update(value=direction_value)
                    else:
                        # 无修改，直接跳转
                        new_model_id = nav_func(index, model_id)
                        return gr.update(value=new_model_id), gr.update(visible=False), gr.update()
                return wrapper
            
            # 上一个/下一个按钮
            nav_inputs = [current_index, model_id_display] + field_components + checkbox_components
            nav_outputs = [model_id_display, confirm_modal, nav_direction]
            
            prev_btn.click(
                fn=check_and_nav(go_prev, "prev"),
                inputs=nav_inputs,
                outputs=nav_outputs
            )
            next_btn.click(
                fn=check_and_nav(go_next, "next"),
                inputs=nav_inputs,
                outputs=nav_outputs
            )
            
            # 导出
            if export_btn:
                def export_to_jsonl():
                    try:
                        # 使用TaskManager中配置的导出目录
                        filepath = self.data_handler.export_to_jsonl(output_dir=self.export_dir)
                        filename = os.path.basename(filepath)
                        return gr.update(value=f"✅ 导出成功: {filename}", visible=True)
                    except PermissionError:
                        error_msg = f"导出失败: 没有写入权限，请检查目录 '{self.export_dir}' 的访问权限"
                        print(f"❌ {error_msg}")
                        return gr.update(value=f"❌ {error_msg}", visible=True)
                    except OSError as e:
                        error_msg = f"导出失败: 文件系统错误 - {str(e)}"
                        print(f"❌ {error_msg}")
                        return gr.update(value=f"❌ {error_msg}", visible=True)
                    except Exception as e:
                        # 记录详细错误信息
                        error_msg = str(e)
                        print(f"❌ 导出错误详情: {error_msg}")
                        return gr.update(value=f"❌ 导出失败: {error_msg}", visible=True)
                
                export_btn.click(fn=export_to_jsonl, outputs=[export_status])
            
            # 确认弹窗按钮
            def save_and_continue_nav(index, model_id, direction, *field_values_and_checkboxes):
                """保存并继续"""
                # 先保存
                save_result = save_data(index, model_id, *field_values_and_checkboxes)
                
                # 检查是否包含错误状态（通过查找HTML中的错误标记）
                has_error = False
                for item in save_result:
                    if isinstance(item, str) and "❌ 保存失败" in item:
                        has_error = True
                        break
                
                # 如果有错误，保持弹窗可见，不进行导航
                if has_error:
                    return gr.update(value=model_id), gr.update(visible=True)
                
                # 无错误，执行导航
                if direction == "prev":
                    new_model_id = go_prev(index, model_id)
                else:
                    new_model_id = go_next(index, model_id)
                
                return gr.update(value=new_model_id), gr.update(visible=False)
            
            def skip_and_continue_nav(index, model_id, direction):
                """放弃修改并继续"""
                if direction == "prev":
                    new_model_id = go_prev(index, model_id)
                else:
                    new_model_id = go_next(index, model_id)
                
                return gr.update(value=new_model_id), gr.update(visible=False)
            
            save_and_continue_inputs = [current_index, model_id_display, nav_direction] + field_components + checkbox_components
            save_and_continue.click(
                fn=save_and_continue_nav,
                inputs=save_and_continue_inputs,
                outputs=[model_id_display, confirm_modal]
            )
            
            skip_changes.click(
                fn=skip_and_continue_nav,
                inputs=[current_index, model_id_display, nav_direction],
                outputs=[model_id_display, confirm_modal]
            )
            
            cancel_nav.click(fn=lambda: gr.update(visible=False), outputs=[confirm_modal])
        
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
    
    def _refresh_visible_keys(self):
        """重新计算用户可见的数据键列表"""
        # 重新计算可见键（不使用缓存，直接从all_data计算）
        self.visible_keys = []
        for key, value in self.all_data.items():
            attrs = self.data_handler.parse_item(value)
            item_uid = attrs.get('uid', '')
            if not item_uid or item_uid == self.user_uid:
                self.visible_keys.append(key)
    
    def get_allowed_paths(self):
        """
        从数据库数据中提取允许访问的基础路径（用于Gradio的allowed_paths）
        
        从image_url字段中提取第一个路径段，适配不同项目的路径结构
        """
        # 如果数据库为空，使用配置的默认路径
        if not self.all_data:
            return [self.default_allowed_path]
        
        # 从第一个数据项的image_url中提取基础路径
        first_item = list(self.all_data.values())[0]
        attrs = self.data_handler.parse_item(first_item)
        image_url = attrs.get('image_url', '')
        
        if image_url and image_url.startswith('/'):
            # 提取第一个路径段（根目录下的第一级目录）
            # 例如: /mnt/data/... -> /mnt
            #      /data/images/... -> /data
            #      /home/user/... -> /home
            parts = image_url.split('/')
            if len(parts) >= 2 and parts[1]:
                base_path = f"/{parts[1]}"
                return [base_path]
        
        # 如果没有找到有效路径，使用默认值
        return [self.default_allowed_path]
        
    # UI状态管理相关方法已移除


def create_login_interface(auth_handler, task_config, debug, dev_user=None):
    """
    创建统一的登录和标注界面，登录成功后直接切换显示
    
    Args:
        auth_handler: 认证处理器
        task_config: 任务配置
        debug: 是否为调试模式
        dev_user: 开发模式用户，如果指定则自动跳过登录
    """
    
    # 先创建标注界面管理器（使用临时用户，获取配置）
    temp_manager = TaskManager(task_config, "temp_user", debug=debug)
    
    # 如果数据未初始化，直接返回错误提示
    if not temp_manager.data_handler:
        with gr.Blocks() as error_demo:
            gr.Markdown("# ⚠️ 数据库未初始化\n运行: `python -m importers.annotation_importer`")
        return error_demo
    
    with gr.Blocks(title=temp_manager.ui_config['title'], css=temp_manager.custom_css) as unified_demo:
        logged_in_user = gr.State(value=dev_user)  # 设置初始用户
        current_manager_state = gr.State(value=None)
        
        # 登录面板（初始显示，如果是开发模式则隐藏）
        with gr.Column(visible=(dev_user is None), elem_id="login_panel") as login_panel:
            gr.Markdown(f"# 🔐 {temp_manager.ui_config['title']}")
            gr.Markdown("## 登录")
            
            with gr.Column():
                login_username = gr.Textbox(label="用户名", placeholder="输入用户名")
                login_password = gr.Textbox(label="密码", type="password", placeholder="输入密码")
                login_btn = gr.Button("登录", variant="primary", size="lg")
                login_status = gr.Textbox(label="状态", interactive=False, visible=False)
        
        # 标注界面面板（登录后显示，如果是开发模式则初始显示）
        with gr.Column(visible=(dev_user is not None)) as annotation_panel:
            # 使用ComponentFactory创建界面组件
            factory = ComponentFactory()
            
            # 预先创建标注界面的所有组件（初始隐藏）
            annotation_components = {}
            
            # 用户信息
            if temp_manager.ui_config.get('show_user_info'):
                annotation_components['user_info'] = gr.HTML(value="")
            
            annotation_components['current_index'] = gr.State(value=0)
            annotation_components['nav_direction'] = gr.State(value="next")
            
            # 使用布局配置构建界面（同时创建和渲染组件）
            factory.build_layout(temp_manager.components_config, temp_manager.layout_config)
            
            # 获取创建的组件
            components = factory.get_all_components()
            
            # 提取字段组件和checkbox组件
            field_components = []
            checkbox_components = []
            for field_config in temp_manager.field_configs:
                field_id = field_config['key']
                comp = components.get(field_id)
                if isinstance(comp, tuple):
                    # (textbox, checkbox) 元组
                    field_components.append(comp[0])
                    checkbox_components.append(comp[1])
                else:
                    field_components.append(comp)
            
            # 获取其他组件
            annotation_components['gif_display'] = components.get('image_url')
            annotation_components['image_p1'] = components.get('image_url_p1')
            annotation_components['image_p2'] = components.get('image_url_p2')
            annotation_components['model_id_display'] = components.get('model_id')
            annotation_components['status_box'] = components.get('annotation_status')
            annotation_components['progress'] = components.get('progress_box')
            annotation_components['scale_slider'] = components.get('scale_slider')
            annotation_components['prev_btn'] = components.get('prev_btn')
            annotation_components['next_btn'] = components.get('next_btn')
            annotation_components['save_btn'] = components.get('save_btn')
            annotation_components['field_components'] = field_components
            annotation_components['checkbox_components'] = checkbox_components
            
            # 导出按钮
            if not debug and temp_manager.data_source == 'database':
                with gr.Row():
                    annotation_components['export_btn'] = gr.Button("📤 导出为JSONL", variant="secondary", size="lg")
                    annotation_components['export_status'] = gr.Textbox(label="导出状态", interactive=False, visible=False)
            
            # 确认弹窗
            with gr.Column(visible=False, elem_id="confirm_modal") as confirm_modal:
                with gr.Column(elem_id="confirm_card"):
                    gr.HTML("<h2>⚠️ 有未保存的修改</h2><p>是否继续？</p>")
                    with gr.Row():
                        annotation_components['save_and_continue'] = gr.Button("💾 保存并继续", variant="primary", size="sm")
                        annotation_components['cancel_nav'] = gr.Button("❌ 取消", variant="secondary", size="sm")
                    annotation_components['skip_changes'] = gr.Button("⚠️ 放弃更改", variant="stop", size="sm")
                    annotation_components['confirm_modal'] = confirm_modal
        
        # 登录逻辑
        def do_login(username, password):
            if not username or not password:
                return (
                    gr.update(value="请输入用户名和密码", visible=True),
                    None,
                    None,
                    gr.update(visible=True),  # 保持登录面板可见
                    gr.update(visible=False)  # 保持标注面板隐藏
                ) + tuple([gr.update()] * 20)  # 空更新
            
            result = auth_handler.login(username, password)
            if result["success"]:
                # 登录成功：创建标注界面管理器并初始化界面
                username_value = result["user"]["username"]
                manager = TaskManager(task_config, username_value, debug=debug)
                
                # 创建新的ComponentFactory实例
                factory = ComponentFactory()
                
                # 使用布局配置构建界面
                factory.build_layout(manager.components_config, manager.layout_config)
                
                # 初始化标注界面数据
                init_data = load_annotation_data(manager, 0)
                
                # 隐藏登录面板，显示标注面板，并加载初始数据
                return (
                    gr.update(visible=False),  # 隐藏登录状态
                    username_value,  # 保存用户名
                    manager,  # 保存manager
                    gr.update(visible=False),  # 隐藏登录面板
                    gr.update(visible=True)    # 显示标注面板
                ) + tuple(init_data)  # 加载初始数据
            else:
                return (
                    gr.update(value=result["message"], visible=True),
                    None,
                    None,
                    gr.update(visible=True),  # 保持登录面板可见
                    gr.update(visible=False)  # 保持标注面板隐藏
                ) + tuple([gr.update()] * 20)  # 空更新
        
        # 标注界面数据加载函数（复用 TaskManager 的逻辑）
        def load_annotation_data(manager, index):
            """加载标注界面数据（重构版）"""
            if not manager or not manager.visible_keys or index >= len(manager.visible_keys):
                # 返回空数据
                # 获取组件数量
                components = factory.get_all_components()
                total = len(components) + 1  # +1 for original_dimensions state
                return tuple([gr.update()] * total)

            model_id = manager.visible_keys[index]
            item = manager.all_data.get(model_id)
            if not item:
                # 如果找不到项目，也返回空数据
                return load_annotation_data(None, 0)
                
            attrs = manager.data_handler.parse_item(item)

            # 浏览即占有
            current_uid = attrs.get('uid', '')
            if not current_uid:
                if hasattr(manager.data_handler, "assign_to_user"):
                    manager.data_handler.assign_to_user(model_id, manager.user_uid)
                    print(f"🔒 占有数据: {model_id} -> {manager.user_uid}")
                    manager.all_data = manager.data_handler.load_data()
                    manager._refresh_visible_keys()
                    item = manager.all_data.get(model_id, item) # 重新获取
                    attrs = manager.data_handler.parse_item(item)

            # --- 按顺序构建所有UI组件的更新 ---
            outputs = []
            
            # 1. 图片组件
            is_part_annotation = manager.task_name == 'part_annotation'
            image_keys = ['image_url', 'image_url_p1', 'image_url_p2'] if is_part_annotation else ['gif_display']
            
            # 修正：确保使用正确的组件ID
            if is_part_annotation:
                image_comp_ids = ['gif_display', 'image_p1', 'image_p2']
                image_data_keys = ['image_url', 'image_url_p1', 'image_url_p2']
            else:
                image_comp_ids = ['gif_display']
                image_data_keys = ['image_url']

            for key in image_data_keys:
                img_path = attrs.get(key)
                if img_path and not os.path.exists(img_path):
                    img_path = None
                outputs.append(gr.update(value=img_path))

            # 2. Model ID
            outputs.append(gr.update(value=model_id))

            # 3. 字段 (Textbox) 和 Checkbox
            field_updates = []
            checkbox_updates = []
            
            # 确保字段顺序与UI一致
            sorted_fields = sorted(manager.field_configs, key=lambda x: (
                ['object_name', 'object_dimension', 'label', 'name'].index(x['key'])
                if x['key'] in ['object_name', 'object_dimension', 'label', 'name']
                else float('inf')
            ))
            
            all_fields_config = temp_manager.field_configs
            
            # 获取UI上实际的字段顺序
            if is_part_annotation:
                left_keys = ['object_name', 'object_dimension', 'label', 'name']
                right_keys = ['dimension', 'material', 'density', 'mass']
                
                left_fields = [f for f in all_fields_config if f['key'] in left_keys]
                right_fields = [f for f in all_fields_config if f['key'] in right_keys]
                
                # 确保dimension在滑块之前
                dim_field = next((f for f in right_fields if f['key'] == 'dimension'), None)
                other_right = [f for f in right_fields if f['key'] != 'dimension']
                
                if dim_field:
                    ordered_fields = left_fields + [dim_field] + other_right
                else:
                    ordered_fields = left_fields + other_right
            else:
                ordered_fields = all_fields_config


            for field in ordered_fields:
                value = attrs.get(field['key'], '')
                processed_value = manager.field_processor.process_load(field, value)
                is_interactive = field.get('interactive', True)
                
                field_updates.append(gr.update(value=processed_value, interactive=is_interactive))
                
                if field.get('has_checkbox') and manager.ui_config.get('enable_checkboxes'):
                    chk_value = attrs.get(f"chk_{field['key']}", False)
                    checkbox_updates.append(gr.update(value=chk_value))
            
            outputs.extend(field_updates)
            outputs.extend(checkbox_updates)

            # 4. 状态框
            if manager.ui_config.get('show_status'):
                status_html = manager._render_status(attrs.get('annotated', False))
                outputs.append(gr.update(value=status_html))

            # 5. 进度条
            prog = f"{index + 1} / {len(manager.visible_keys)}"
            outputs.append(gr.update(value=prog))

            return tuple(outputs)
        
        # 标注界面的事件处理函数（需要manager状态）
        def _resolve_model_for_annotation(manager, index, model_id):
            """解析当前模型（用于标注界面）"""
            if not manager or not manager.visible_keys:
                return 0, None
            resolved_model = None
            resolved_index = index
            if model_id and model_id in manager.visible_keys:
                resolved_model = model_id
                resolved_index = manager.visible_keys.index(model_id)
            elif 0 <= index < len(manager.visible_keys):
                resolved_model = manager.visible_keys[index]
            return resolved_index, resolved_model
        
        def save_annotation_data(manager, index, model_id, *values):
            """保存标注数据"""
            if not manager:
                return tuple([gr.update()] * 20)
            
            resolved_index, resolved_model = _resolve_model_for_annotation(manager, index, model_id)
            if resolved_model is None:
                return tuple(load_annotation_data(manager, resolved_index))
            
            num_fields = len(manager.field_configs)
            field_values = values[:num_fields]
            checkbox_values = values[num_fields:]
            
            save_dict = {}
            checkbox_idx = 0
            has_error = False
            
            for idx, field in enumerate(manager.field_configs):
                key = field['key']
                # 只保存可交互的字段
                if field.get('interactive', True):
                    save_dict[key] = manager.field_processor.process_save(field, field_values[idx])
                
                if field.get('has_checkbox'):
                    chk_value = checkbox_values[checkbox_idx]
                    save_dict[f"chk_{key}"] = chk_value
                    if chk_value:
                        has_error = True
                    checkbox_idx += 1
            
            score = 0 if has_error else 1
            
            # 直接使用data_handler保存
            result = manager.data_handler.save_item(
                resolved_model,
                save_dict,
                score=score,
                uid=manager.user_uid
            )
            
            if isinstance(result, dict) and not result.get("success", True):
                error_msg = result.get("message", "未知错误")
                print(f"❌ 保存失败: {error_msg}")
            else:
                print(f"✅ 保存: {resolved_model}, score={score}, uid={manager.user_uid}")
                
            # 重新加载数据
            manager.all_data = manager.data_handler.load_data()
            manager._refresh_visible_keys()
                
            return tuple(load_annotation_data(manager, resolved_index))
        
        def check_modified_annotation(manager, index, model_id, *values):
            """检查标注数据是否修改"""
            if not manager or not manager.visible_keys:
                return False
            
            resolved_index, resolved_model = _resolve_model_for_annotation(manager, index, model_id)
            if resolved_model is None:
                return False
            
            item = manager.all_data.get(resolved_model)
            if item is None:
                return False
            
            attrs = manager.data_handler.parse_item(item)
            num_fields = len(manager.field_configs)
            field_values = values[:num_fields]
            checkbox_values = values[num_fields:]
            
            original_values = []
            for field in manager.field_configs:
                value = attrs.get(field['key'], '')
                original_values.append(manager.field_processor.process_load(field, value))
            
            for idx in range(num_fields):
                orig = original_values[idx] if original_values[idx] is not None else ''
                curr = field_values[idx] if field_values[idx] is not None else ''
                if str(orig) != str(curr):
                    return True
            
            checkbox_idx = 0
            for field in manager.field_configs:
                if field.get('has_checkbox'):
                    original_chk = attrs.get(f"chk_{field['key']}", False)
                    current_chk = checkbox_values[checkbox_idx]
                    if original_chk != current_chk:
                        return True
                    checkbox_idx += 1
            
            return False
        
        def navigate_annotation_with_check(manager, index, model_id, direction, *values):
            """
            标注界面导航（带修改检测）- 返回操作字典
            """
            if not manager:
                return {"action": "none"}

            resolved_index, resolved_model = _resolve_model_for_annotation(manager, index, model_id)
            modified = check_modified_annotation(manager, resolved_index, resolved_model, *values)

            if modified:
                # 有修改，请求显示弹窗
                return {
                    "action": "show_confirm",
                    "index": resolved_index,
                    "direction": direction
                }
            else:
                # 无修改，直接导航
                if direction == "next":
                    new_index = min(len(manager.visible_keys) - 1, resolved_index + 1)
                else:
                    new_index = max(0, resolved_index - 1)
                
                return {
                    "action": "navigate",
                    "new_index": new_index
                }

        def navigate_wrapper(manager, index, model_id, direction, *values):
            """
            导航包装器：根据检查结果动态构建Gradio更新
            """
            result = navigate_annotation_with_check(manager, index, model_id, direction, *values)
            
            action = result.get("action")
            
            if action == "show_confirm":
                # 显示确认弹窗
                return (
                    gr.update(value=result["index"]),
                    gr.update(visible=True),
                    gr.update(value=result["direction"])
                ) + tuple([gr.update()] * len(annotation_outputs))
            
            elif action == "navigate":
                # 直接导航
                new_index = result["new_index"]
                return (
                    gr.update(value=new_index),
                    gr.update(visible=False),
                    gr.update()
                ) + tuple(load_annotation_data(manager, new_index))
            
            else: # action == "none"
                # 无操作
                return (gr.update(), gr.update(), gr.update()) + tuple([gr.update()] * len(annotation_outputs))
        
        def save_and_nav_annotation(manager, index, model_id, direction, *values):
            """保存并继续"""
            if not manager:
                return tuple([gr.update()] * 20)
            
            # 先保存
            save_result = save_annotation_data(manager, index, model_id, *values)
            
            # 再跳转
            resolved_index, _ = _resolve_model_for_annotation(manager, index, model_id)
            if direction == "next":
                new_index = min(len(manager.visible_keys) - 1, resolved_index + 1)
            else:
                new_index = max(0, resolved_index - 1)
            
            return (
                gr.update(value=new_index),
                gr.update(visible=False)
            ) + tuple(load_annotation_data(manager, new_index))
        
        def skip_and_nav_annotation(manager, index, model_id, direction):
            """放弃更改并继续"""
            if not manager:
                return tuple([gr.update()] * 20)
            
            resolved_index, _ = _resolve_model_for_annotation(manager, index, model_id)
            if direction == "next":
                new_index = min(len(manager.visible_keys) - 1, resolved_index + 1)
            else:
                new_index = max(0, resolved_index - 1)
            
            return (
                gr.update(value=new_index),
                gr.update(visible=False)
            ) + tuple(load_annotation_data(manager, new_index))
        
        # 计算输出组件列表
        status_outputs = [annotation_components['status_box']] if 'status_box' in annotation_components else []
        
        # 根据任务类型决定使用哪些图片组件
        if temp_manager.task_name == 'part_annotation':
            # part_annotation使用三张图片
            image_outputs = [
                annotation_components['gif_display'],
                annotation_components['image_p1'],
                annotation_components['image_p2'],
            ]
        else:
            # 默认模式只有一张图片
            image_outputs = [annotation_components['gif_display']]
        
        # 合并所有输出
        annotation_outputs = image_outputs + [
            annotation_components['model_id_display'],
        ] + annotation_components['field_components'] + annotation_components['checkbox_components'] + status_outputs + [annotation_components['progress']]
        
        # 事件绑定 - 登录
        login_btn.click(
            do_login,
            inputs=[login_username, login_password],
            outputs=[
                login_status, 
                logged_in_user, 
                current_manager_state,
                login_panel, 
                annotation_panel,
            ] + annotation_outputs
        )
        
        # 事件绑定 - 标注界面（使用lambda包装以传递manager）
        annotation_components['save_btn'].click(
            lambda mgr, idx, mid, *vals: save_annotation_data(mgr, idx, mid, *vals),
            inputs=[current_manager_state, annotation_components['current_index'], annotation_components['model_id_display']] + 
                   annotation_components['field_components'] + annotation_components['checkbox_components'],
            outputs=annotation_outputs
        )
        
        annotation_components['prev_btn'].click(
            navigate_wrapper,
            inputs=[current_manager_state, annotation_components['current_index'], annotation_components['model_id_display'],
                   gr.State("prev")] + annotation_components['field_components'] + annotation_components['checkbox_components'],
            outputs=[annotation_components['current_index'], annotation_components['confirm_modal'], annotation_components['nav_direction']] + annotation_outputs
        )
        
        annotation_components['next_btn'].click(
            navigate_wrapper,
            inputs=[current_manager_state, annotation_components['current_index'], annotation_components['model_id_display'],
                   gr.State("next")] + annotation_components['field_components'] + annotation_components['checkbox_components'],
            outputs=[annotation_components['current_index'], annotation_components['confirm_modal'], annotation_components['nav_direction']] + annotation_outputs
        )
        
        annotation_components['save_and_continue'].click(
            lambda mgr, idx, mid, dir, *vals: save_and_nav_annotation(mgr, idx, mid, dir, *vals),
            inputs=[current_manager_state, annotation_components['current_index'], annotation_components['model_id_display'], 
                   annotation_components['nav_direction']] + annotation_components['field_components'] + annotation_components['checkbox_components'],
            outputs=[annotation_components['current_index'], annotation_components['confirm_modal']] + annotation_outputs
        )
        
        annotation_components['skip_changes'].click(
            lambda mgr, idx, mid, dir: skip_and_nav_annotation(mgr, idx, mid, dir),
            inputs=[current_manager_state, annotation_components['current_index'], annotation_components['model_id_display'], annotation_components['nav_direction']],
            outputs=[annotation_components['current_index'], annotation_components['confirm_modal']] + annotation_outputs
        )
        
        annotation_components['cancel_nav'].click(
            lambda: gr.update(visible=False),
            outputs=[annotation_components['confirm_modal']]
        )
        
        # 导出按钮事件
        if 'export_btn' in annotation_components:
            def export_annotation_data(manager):
                """导出标注数据"""
                if not manager or not hasattr(manager.data_handler, 'export_to_jsonl'):
                    return gr.update(value="❌ 导出功能不可用", visible=True)
                try:
                    # 使用配置的导出目录
                    filepath = manager.data_handler.export_to_jsonl(output_dir=manager.export_dir)
                    filename = os.path.basename(filepath)
                    return gr.update(value=f"✅ 导出成功: {filename}", visible=True)
                except PermissionError:
                    error_msg = f"导出失败: 没有写入权限，请检查目录 '{manager.export_dir}' 的访问权限"
                    print(f"❌ {error_msg}")
                    return gr.update(value=f"❌ {error_msg}", visible=True)
                except OSError as e:
                    error_msg = f"导出失败: 文件系统错误 - {str(e)}"
                    print(f"❌ {error_msg}")
                    return gr.update(value=f"❌ {error_msg}", visible=True)
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ 导出错误详情: {error_msg}")
                    return gr.update(value=f"❌ 导出失败: {error_msg}", visible=True)
            
            annotation_components['export_btn'].click(
                lambda mgr: export_annotation_data(mgr),
                inputs=[current_manager_state],
                outputs=[annotation_components['export_status']]
            )
        
        # 初始化标注界面（登录成功后自动加载第一项）
        def init_annotation_on_login(manager):
            """登录成功后初始化标注界面"""
            if manager:
                return tuple(load_annotation_data(manager, 0))
            return tuple([gr.update()] * len(annotation_outputs))
        
        # 当manager状态改变时，初始化标注界面
        current_manager_state.change(
            init_annotation_on_login,
            inputs=[current_manager_state],
            outputs=annotation_outputs
        )
        
        # 如果是自动登录模式，在界面加载后自动创建管理器并初始化界面
        if dev_user:  # 使用dev_user替代未定义的auto_login_user
            def auto_login():
                manager = TaskManager(task_config, dev_user, debug=debug)
                # 返回manager和所有输出组件的值，确保输出数量匹配
                output_values = load_annotation_data(manager, 0)
                # 将列表转换为元组，这样可以与其他元组连接
                return (manager,) + tuple(output_values)  # 使用tuple()将列表转换为元组
                
            unified_demo.load(
                fn=auto_login,
                outputs=[current_manager_state] + annotation_outputs
            )
        
        # 上面已经处理了dev_user模式下的自动登录，这里不需要重复
    
    return unified_demo


def main():
    parser = argparse.ArgumentParser(description='标注工具 - 支持多任务')
    parser.add_argument('--port', type=int, default=None, help='端口（不指定则使用任务默认端口）')
    parser.add_argument('--task', type=str, default=None, help='任务名称（如: annotation, review）')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug模式：使用test.jsonl文件')
    parser.add_argument('--dev', action='store_true', help='开发模式：跳过登录，直接使用指定用户')
    parser.add_argument('--uid', type=str, default='dev_user', help='开发模式下的用户ID（仅在--dev模式下使用）')
    parser.add_argument('--list-tasks', action='store_true', help='列出所有可用任务')
    
    args = parser.parse_args()
    
    # 列出所有任务
    if args.list_tasks:
        print("\n📋 可用任务列表:")
        print("=" * 60)
        for idx, route in enumerate(ROUTES, 1):
            print(f"{idx}. {route['task']}")
            print(f"   描述: {route['description']}")
            print(f"   端口: {route['port']}")
            print(f"   数据库: databases/{route['task']}.db")
            print(f"   配置: ui_configs/{route['task']}_config.py")
            print()
        print("使用方式: python src/main_multi.py --task <任务名>")
        print("=" * 60)
        return
    
    # 选择任务
    if args.task:
        # 根据任务名查找配置
        task_config = None
        for route in ROUTES:
            if route['task'] == args.task:
                task_config = route
                break
        
        if not task_config:
            print(f"❌ 错误: 未找到任务 '{args.task}'")
            print(f"\n可用任务: {', '.join([r['task'] for r in ROUTES])}")
            print(f"使用 --list-tasks 查看详细信息")
            return
    else:
        # 默认使用第一个任务
        task_config = ROUTES[0]
        print(f"💡 未指定任务，使用默认任务: {task_config['task']}")
    
    # 端口选择（命令行 > 任务配置 > 默认）
    if args.port is None:
        args.port = task_config.get('port', DEFAULT_PORT)
    
    # 判断是否需要登录
    if args.dev:
        # 开发模式：跳过登录，直接使用指定用户
        user_uid = args.uid
        print(f"\n{'='*60}")
        print(f"⚡ 开发模式（跳过登录）")
        print(f"{'='*60}")
        print(f"🚀 {task_config['description']}")
        print(f"用户: {user_uid}")
        print(f"端口: {args.port}")
        print(f"模式: {'🐛 Debug' if args.debug else '🗄️  正常'}")
        print(f"{'='*60}\n")
        
        # 直接创建标注界面
        manager = TaskManager(task_config, user_uid, debug=args.debug)
        
        # 创建登录界面（即使是开发模式也使用统一界面，只是自动登录）
        from src.auth_handler import AuthHandler
        auth_handler = AuthHandler()
        demo = create_login_interface(auth_handler, task_config, args.debug, dev_user=user_uid)
        
        # 使用manager获取允许的路径（与用户相关）
        allowed_paths = manager.get_allowed_paths()
        
        # 使用统一界面启动
        demo.launch(
            server_port=args.port,
            server_name="0.0.0.0",
            allowed_paths=allowed_paths,
            show_api=False  # 禁用API文档，避免启动检查问题
        )
    else:
        # 生产模式：需要登录
        from src.auth_handler import AuthHandler
        auth_handler = AuthHandler()
        
        print(f"\n{'='*60}")
        print(f"🔐 物体属性标注工具")
        print(f"{'='*60}")
        print(f"端口: {args.port}")
        print(f"模式: {'🐛 Debug' if args.debug else '🗄️  正常'}")
        print(f"使用 --dev 参数可跳过登录（开发模式）")
        print(f"{'='*60}\n")
        
        # 创建登录界面
        demo = create_login_interface(auth_handler, task_config, args.debug)
        
        # 创建与登录用户相关的临时管理器以获取正确的路径权限
        # 使用 "temp_user" 是为了确保它与开发模式的行为一致
        temp_manager = TaskManager(task_config, "temp_user", debug=args.debug)
        allowed_paths = temp_manager.get_allowed_paths()
        
        demo.launch(
            server_port=args.port,
            server_name="0.0.0.0",
            allowed_paths=allowed_paths,
            show_api=False  # 禁用API文档，避免启动检查问题
        )


if __name__ == "__main__":
    main()

