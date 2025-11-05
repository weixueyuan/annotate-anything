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
        
        # 组件引用
        self.components = {}
        self.factory = None
    
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
                print(f"   请先导入数据: python -m importers.generic_importer")
                self.data_handler = None
                self.all_data = {}
                self.visible_keys = []
                return
        
        # 加载所有数据
        self.all_data = self.data_handler.load_data()
        
        # 过滤可见数据
        self._refresh_visible_keys()
        
        print(f"✓ 加载完成")
        print(f"  总数: {len(self.all_data)}, 可见: {len(self.visible_keys)}")
    
    def _refresh_visible_keys(self):
        """重新计算用户可见的数据键列表"""
        self.visible_keys = []
        for key, value in self.all_data.items():
            attrs = self.data_handler.parse_item(value)
            item_uid = attrs.get('uid', '')
            if not item_uid or item_uid == self.user_uid:
                self.visible_keys.append(key)
    
    def build_interface(self):
        """构建界面"""
        if not self.data_handler:
            with gr.Blocks() as demo:
                gr.Markdown(f"# ⚠️ 数据库未初始化\n运行: `python tools/import_to_db.py`")
            return demo
        
        # 创建组件工厂
        self.factory = ComponentFactory()
        
        with gr.Blocks(title=self.ui_config['title'], css=self.custom_css) as demo:
            gr.Markdown(f"# {self.ui_config['title']}")
            
            # 用户信息
            if self.ui_config.get('show_user_info'):
                other_count = len(self.all_data) - len(self.visible_keys)
                _ = gr.HTML(self._render_user_info(len(self.visible_keys), other_count))
            
            # State组件
            self.components['current_index'] = gr.State(value=0)
            self.components['nav_direction'] = gr.State(value="next")
            
            # 动态查找尺度滑块的目标字段
            self.dimension_field_name = None
            for comp_config in self.components_config:
                if comp_config.get('type') == 'slider' and comp_config.get('target_field'):
                    self.dimension_field_name = comp_config.get('target_field')
                    break
            
            self.components['original_dimensions'] = gr.State(value="")  # 存储原始dimension/dimensions值
            
            # 使用布局配置构建界面（同时创建和渲染组件）
            self.factory.build_layout(self.components_config, self.layout_config)
            
            # 获取创建的组件
            self.components.update(self.factory.get_all_components())
            
            # 导出按钮（仅在正常模式下显示）
            if not self.debug and self.data_source == 'database':
                with gr.Row():
                    self.components['export_btn'] = gr.Button("📤 导出为JSONL", variant="secondary", size="lg")
                    self.components['export_status'] = gr.Textbox(label="导出状态", interactive=False, visible=False)
            
            # 确认弹窗
            with gr.Column(visible=False, elem_id="confirm_modal") as confirm_modal:
                with gr.Column(elem_id="confirm_card"):
                    gr.HTML("<h2>⚠️ 有未保存的修改</h2><p>是否继续？</p>")
                    with gr.Row():
                        self.components['save_and_continue'] = gr.Button("💾 保存并继续", variant="primary", size="sm")
                        self.components['cancel_nav'] = gr.Button("❌ 取消", variant="secondary", size="sm")
                    self.components['skip_changes'] = gr.Button("⚠️ 放弃更改", variant="stop", size="sm")
            
            self.components['confirm_modal'] = confirm_modal
            
            # 在Blocks上下文中绑定事件
            self._bind_events(demo)
            
        return demo
    
    def _bind_events(self, demo):
        """绑定所有事件处理函数"""
        # 提取字段组件和checkbox组件
        field_components = []
        checkbox_components = []
        for field_config in self.field_configs:
            field_id = field_config['key']
            comp = self.components.get(field_id)
            if isinstance(comp, tuple):
                # (textbox, checkbox) 元组
                field_components.append(comp[0])
                checkbox_components.append(comp[1])
            else:
                field_components.append(comp)
        
        # 保存组件引用，方便后续使用
        self.field_components = field_components
        self.checkbox_components = checkbox_components
        
        # 获取其他组件
        model_id_display = self.components.get('model_id')
        scale_slider = self.components.get('scale_slider')
        prev_btn = self.components.get('prev_btn')
        next_btn = self.components.get('next_btn')
        save_btn = self.components.get('save_btn')
        
        # 构建 load_outputs（按照COMPONENTS配置顺序，跳过按钮）
        load_outputs = []
        for comp_config in self.components_config:
            comp_id = comp_config['id']
            comp_type = comp_config['type']
            
            # 跳过按钮组件
            if comp_type == 'button':
                continue
            
            comp = self.components.get(comp_id)
            if comp:
                # 如果是元组（textbox + checkbox），展开添加
                if isinstance(comp, tuple):
                    load_outputs.extend(comp)
                else:
                    load_outputs.append(comp)
        
        # 添加 original_dimensions state
        load_outputs.append(self.components['original_dimensions'])
        self.load_outputs = load_outputs  # 保存以备后用
        
        # 页面加载时加载数据
        demo.load(fn=self.load_data, inputs=[self.components['current_index']], outputs=self.load_outputs)
        
        # 移除 model_id 变化时自动加载数据的事件
        # 只保留按回车键触发的搜索事件，避免用户修改但未按回车时触发搜索
        
        # 滑块变化时更新dimension/dimensions字段
        if self.dimension_field_name and scale_slider:
            dimensions_idx = None
            for i, field in enumerate(self.field_configs):
                if field['key'] == self.dimension_field_name:
                    dimensions_idx = i
                    break
            
            if dimensions_idx is not None:
                scale_slider.change(
                    fn=self.scale_dimensions,
                    inputs=[self.components['original_dimensions'], scale_slider],
                    outputs=[field_components[dimensions_idx]]
                )
        
        # 搜索功能（按回车触发）- model_id既显示也可搜索
        if model_id_display:
            search_outputs = [self.components['current_index']] + self.load_outputs
            model_id_display.submit(
                fn=self.search_and_load,
                inputs=[model_id_display],
                outputs=search_outputs
            )
        
        # 保存
        save_inputs = [self.components['current_index'], model_id_display] + field_components + checkbox_components
        save_btn.click(fn=self.save_data, inputs=save_inputs, outputs=self.load_outputs)
        
        # 导航检查和跳转
        nav_inputs = [self.components['current_index'], model_id_display] + field_components + checkbox_components
        nav_outputs = [self.components['current_index']] + self.load_outputs + [self.components['confirm_modal'], self.components['nav_direction']]
        
        prev_btn.click(
            fn=self.check_and_nav_prev,
            inputs=nav_inputs,
            outputs=nav_outputs
        )
        next_btn.click(
            fn=self.check_and_nav_next,
            inputs=nav_inputs,
            outputs=nav_outputs
        )
        
        # 导出
        if 'export_btn' in self.components:
            self.components['export_btn'].click(
                fn=self.export_to_jsonl,
                outputs=[self.components['export_status']]
            )
        
        # 确认弹窗按钮
        save_and_continue_inputs = [self.components['current_index'], model_id_display, self.components['nav_direction']] + field_components + checkbox_components
        save_and_continue_outputs = [self.components['current_index']] + self.load_outputs + [self.components['confirm_modal']]
        self.components['save_and_continue'].click(
            fn=self.save_and_continue_nav,
            inputs=save_and_continue_inputs,
            outputs=save_and_continue_outputs
        )
        
        skip_and_continue_outputs = [self.components['current_index']] + self.load_outputs + [self.components['confirm_modal']]
        self.components['skip_changes'].click(
            fn=self.skip_and_continue_nav,
            inputs=[self.components['current_index'], model_id_display, self.components['nav_direction']],
            outputs=skip_and_continue_outputs
        )
        
        self.components['cancel_nav'].click(
            fn=lambda: gr.update(visible=False),
            outputs=[self.components['confirm_modal']]
        )
    
    def load_data(self, index):
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
                self._refresh_visible_keys()
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
                if self.dimension_field_name and data_field == self.dimension_field_name:
                    original_dims_value = attrs.get(self.dimension_field_name, '')
            
            # 处理其他图片字段（part_annotation 有多个图片）
            elif comp_type == 'image' and data_field not in ['model_id', '_computed_status']:
                # 其他图片字段（如 image_url_p1, image_url_p2）
                img_path = attrs.get(data_field, None)
                if img_path and not os.path.exists(img_path):
                    img_path = None
                result.append(img_path)
            
            else:
                # 其他普通字段
                value = attrs.get(data_field, '')
                result.append(value)
        
        # 添加 original_dimensions state
        result.append(original_dims_value)
        
        return result
    
    def on_model_id_change(self, model_id_value):
        """model_id 变化时加载对应的数据（已不再使用，保留函数以兼容旧代码）"""
        if not model_id_value or model_id_value not in self.visible_keys:
            return [0] + self.load_data(0)
        new_index = self.visible_keys.index(model_id_value)
        return [new_index] + self.load_data(new_index)
    
    def scale_dimensions(self, original_dims, scale_value):
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
    
    def _resolve_model(self, index, model_id):
        """根据索引和model_id解析当前记录"""
        resolved_model = None
        resolved_index = index
        if model_id and model_id in self.visible_keys:
            resolved_model = model_id
            resolved_index = self.visible_keys.index(model_id)
        elif 0 <= index < len(self.visible_keys):
            resolved_model = self.visible_keys[index]
        return resolved_index, resolved_model
    
    def save_data(self, index, model_id, *values):
        """保存数据"""
        resolved_index, resolved_model = self._resolve_model(index, model_id)
        if resolved_model is None:
            return self.load_data(resolved_index)
        
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
            result = self.load_data(resolved_index)
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
            self._refresh_visible_keys()
            
            return self.load_data(resolved_index)
    
    def search_and_load(self, search_value):
        """
        搜索功能：根据输入的值查找对应的 model_id
        只有在按下回车键时才会执行搜索
        
        Args:
            search_value: model_id输入框的值
            
        Returns:
            更新后的所有组件值
        """
        if not search_value or not search_value.strip():
            # 空搜索，不做任何操作，保持当前数据
            return [self.components['current_index'].value] + self.load_data(self.components['current_index'].value)
        
        search_value = search_value.strip()
        
        # 查找 model_id（在 visible_keys 中）
        if search_value in self.visible_keys:
            # 找到了，跳转到该索引
            new_index = self.visible_keys.index(search_value)
            print(f"🔍 搜索成功: {search_value} (索引 {new_index})")
            return [new_index] + self.load_data(new_index)
        else:
            # 未找到，提示用户，保持当前数据
            print(f"⚠️  未找到: {search_value}")
            return [self.components['current_index'].value] + self.load_data(self.components['current_index'].value)
    
    def has_real_changes(self, index, model_id, *field_values_and_checkboxes):
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
            
            # 忽略 model_id 字段的变化，因为它只是用于搜索，不应该触发保存确认
            if key == 'model_id':
                continue
                
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
    
    def check_and_nav_prev(self, index, model_id, *field_values_and_checkboxes):
        """检查并导航到上一个"""
        return self._check_and_nav(index, model_id, "prev", *field_values_and_checkboxes)
    
    def check_and_nav_next(self, index, model_id, *field_values_and_checkboxes):
        """检查并导航到下一个"""
        return self._check_and_nav(index, model_id, "next", *field_values_and_checkboxes)
    
    def _check_and_nav(self, index, model_id, direction, *field_values_and_checkboxes):
        """导航检查：对比当前值与数据库值，如果有差异显示弹窗，否则直接跳转"""
        if self.has_real_changes(index, model_id, *field_values_and_checkboxes):
            # 有修改，显示弹窗，记录方向
            # 返回与 nav_outputs 数量匹配的 gr.update()
            num_load_outputs = len(self.load_outputs)
            updates = [gr.update()] * (1 + num_load_outputs)  # current_index + load_outputs
            return updates + [gr.update(visible=True), gr.update(value=direction)]
        else:
            # 无修改，直接跳转并加载新数据
            new_index, _ = self._go_direction(index, model_id, direction)
            new_data = self.load_data(new_index)
            return [new_index] + new_data + [gr.update(visible=False), gr.update()]
    
    def _go_direction(self, index, model_id, direction):
        """根据方向导航, 返回 (new_index, new_model_id)"""
        resolved_index, _ = self._resolve_model(index, model_id)
        if direction == "prev":
            new_index = max(0, resolved_index - 1)
        else:
            new_index = min(len(self.visible_keys) - 1, resolved_index + 1)
        
        new_model_id = self.visible_keys[new_index] if new_index < len(self.visible_keys) else ""
        return new_index, new_model_id
    
    def save_and_continue_nav(self, index, model_id, direction, *field_values_and_checkboxes):
        """保存并继续"""
        # 先保存
        save_result_payload = self.save_data(index, model_id, *field_values_and_checkboxes)
        
        # 检查保存是否成功
        has_error = any(isinstance(item, str) and "❌ 保存失败" in item for item in save_result_payload)
        
        if has_error:
            # 保存失败, 不导航, 保持弹窗可见, 并更新UI以显示错误信息
            resolved_index, _ = self._resolve_model(index, model_id)
            return [resolved_index] + save_result_payload + [gr.update(visible=True)]
        
        # 保存成功, 执行导航并加载新数据
        new_index, _ = self._go_direction(index, model_id, direction)
        new_data = self.load_data(new_index)
        return [new_index] + new_data + [gr.update(visible=False)]
    
    def skip_and_continue_nav(self, index, model_id, direction):
        """放弃修改并继续"""
        # 执行导航并加载新数据
        new_index, _ = self._go_direction(index, model_id, direction)
        new_data = self.load_data(new_index)
        return [new_index] + new_data + [gr.update(visible=False)]
    
    def export_to_jsonl(self):
        """导出数据为JSONL文件"""
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
    
    def _render_status(self, annotated):
        """渲染标注状态"""
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
        """渲染用户信息"""
        return f'<div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:12px;border-radius:8px;text-align:center;">👤 用户：{self.user_uid} | 📊 可见：{visible} | 🔒 其他：{others}</div>'
    
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


def create_login_interface(auth_handler, task_config, debug, dev_user=None):
    """
    创建统一的登录和标注界面，登录成功后直接切换显示
    
    Args:
        auth_handler: 认证处理器
        task_config: 任务配置
        debug: 是否为调试模式
        dev_user: 开发模式用户，如果指定则自动跳过登录
    """
    
    # 创建临时任务管理器（用于获取UI配置）
    temp_manager = TaskManager(task_config, "temp_user", debug=debug)
    
    # 如果数据未初始化，直接返回错误提示
    if not temp_manager.data_handler:
        with gr.Blocks() as error_demo:
            gr.Markdown("# ⚠️ 数据库未初始化\n运行: `python -m importers.annotation_importer`")
        return error_demo
    
    # 预先创建任务管理器（如果是开发模式）
    manager = None
    if dev_user:
        manager = TaskManager(task_config, dev_user, debug=debug)
    
    # 创建界面
    with gr.Blocks(title=temp_manager.ui_config['title'], css=temp_manager.custom_css) as unified_demo:
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
        with gr.Column(visible=(dev_user is not None), elem_id="annotation_panel") as annotation_panel:
            # 如果是开发模式，直接构建界面
            if manager:
                manager.build_interface()
        
        # 登录逻辑
        def do_login(username, password):
            """处理登录"""
            if not username or not password:
                return gr.update(value="请输入用户名和密码", visible=True), gr.update(visible=True), gr.update(visible=False)
            
            result = auth_handler.login(username, password)
            if result["success"]:
                # 登录成功：创建标注界面管理器
                username_value = result["user"]["username"]
                
                # 返回登录状态和面板可见性
                return gr.update(value="登录成功", visible=False), gr.update(visible=False), gr.update(visible=True)
            else:
                return gr.update(value=result["message"], visible=True), gr.update(visible=True), gr.update(visible=False)
        
        # 绑定登录事件
        login_btn.click(
            fn=do_login,
            inputs=[login_username, login_password],
            outputs=[login_status, login_panel, annotation_panel]
        )
    
    return unified_demo


def main():
    """主函数"""
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
        
        # 创建登录界面（即使是开发模式也使用统一界面，只是自动登录）
        from src.auth_handler import AuthHandler
        auth_handler = AuthHandler()
        demo = create_login_interface(auth_handler, task_config, args.debug, dev_user=user_uid)
        
        # 创建管理器以获取允许的路径
        manager = TaskManager(task_config, user_uid, debug=args.debug)
        allowed_paths = manager.get_allowed_paths()
        
        # 启动服务
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
        
        # 创建管理器以获取允许的路径
        manager = TaskManager(task_config, "temp_user", debug=args.debug)
        allowed_paths = manager.get_allowed_paths()
        
        # 启动服务
        demo.launch(
            server_port=args.port,
            server_name="0.0.0.0",
            allowed_paths=allowed_paths,
            show_api=False  # 禁用API文档，避免启动检查问题
        )


if __name__ == "__main__":
    main()
