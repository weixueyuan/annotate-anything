"""
组件工厂 - 根据配置动态创建Gradio组件

核心设计：
1. id 既是key也是elem_id（消除冗余）
2. 默认从上到下排序（不需要order字段）
3. 布局由 LAYOUT_CONFIG 控制（不需要position字段）
4. elem_id 用于CSS精确控制样式
"""

import gradio as gr
from typing import Dict, Any, List, Union


class ComponentFactory:
    """组件工厂类"""
    
    def __init__(self):
        # 组件类型注册表
        self.component_registry = {
            "image": self._create_image,
            "textbox": self._create_textbox,
            "search": self._create_search,
            "html": self._create_html,
            "button": self._create_button,
            "slider": self._create_slider,
            "checkbox": self._create_checkbox,
        }
        
        # 存储创建的组件（用于后续引用）
        self.components = {}
        
        # 存储checkbox组件（用于字段复选框）
        self.checkboxes = {}
        
        # 组件配置字典（用于按需创建）
        self.components_config_dict = {}
    
    def create_component(self, config: Dict[str, Any]) -> Union[gr.Component, tuple]:
        """
        根据配置创建组件
        
        Args:
            config: 组件配置字典
            
        Returns:
            创建的Gradio组件（可能是单个组件或组件元组）
        """
        comp_type = config.get("type")
        comp_id = config.get("id")
        
        if comp_type not in self.component_registry:
            raise ValueError(f"未知组件类型: {comp_type}")
        
        # 调用对应的创建函数
        creator = self.component_registry[comp_type]
        component = creator(config)
        
        # 存储组件引用
        if comp_id:
            self.components[comp_id] = component
        
        return component
    
    def _create_image(self, config: Dict) -> gr.Image:
        """创建图片组件"""
        # 修复图片label显示问题，确保label始终取自配置
        return gr.Image(
            label=str(config.get("label", "")),
            type="filepath",
            interactive=bool(config.get("interactive", False)),
            elem_id=config.get("id")
        )
    
    def _create_textbox(self, config: Dict) -> Union[gr.Textbox, tuple]:
        """
        创建文本框组件
        
        如果 has_checkbox=True，则返回 (textbox, checkbox) 元组
        
        支持的配置参数:
        - label: 标签文本
        - placeholder: 占位符文本
        - lines: 文本行数
        - interactive: 是否可交互编辑(默认为True)
        - has_checkbox: 是否添加错误检查复选框
        """
        # 获取交互状态（默认为可编辑）
        
        # 如果需要checkbox，先创建checkbox（在textbox上方）
        if config.get("has_checkbox", False):
            # 组合checkbox标签：checkbox_label + 字段label
            checkbox_label = f"{config.get('checkbox_label', '✗')} {config.get('label', '')}"
            checkbox = gr.Checkbox(
                label=checkbox_label,
                value=False,
                container=False,
                elem_id=f"{config.get('id')}_checkbox"
            )
            # 存储checkbox引用
            self.checkboxes[config.get("id")] = checkbox
            
            # 创建textbox（显示原始标签）
            textbox = gr.Textbox(
                label=config.get("label", ""),  # 使用原始标签
                placeholder=config.get("placeholder", ""),
                lines=config.get("lines", 1),
                interactive=bool(config.get("interactive", True)),
                elem_id=config.get("id")
            )
            
            return (textbox, checkbox)
        
        # 没有checkbox的情况，正常创建textbox
        textbox = gr.Textbox(
            label=config.get("label", ""),
            placeholder=config.get("placeholder", ""),
            lines=config.get("lines", 1),
            interactive=bool(config.get("interactive", True)),
            elem_id=config.get("id")
        )
        
        return textbox
    
    def _create_search(self, config: Dict) -> gr.Textbox:
        """
        创建搜索框组件
        
        搜索框是特殊的 textbox，可以配置：
        - searchable: True/False (是否可搜索，默认True)
        - interactive: True/False (是否可编辑，默认根据searchable决定)
        """
        searchable = config.get("searchable", True)
        interactive = config.get("interactive", searchable)
        
        return gr.Textbox(
            label=config.get("label", ""),
            placeholder=config.get("placeholder", "输入后必须按回车键才能搜索" if searchable else ""),
            lines=config.get("lines", 1),
            interactive=bool(interactive),
            elem_id=config.get("id")
        )
    
    def _create_html(self, config: Dict) -> gr.HTML:
        """创建HTML组件"""
        return gr.HTML(
            value=config.get("value", ""),
            elem_id=config.get("id")
        )
    
    def _create_button(self, config: Dict) -> gr.Button:
        """创建按钮组件"""
        return gr.Button(
            value=config.get("label", "按钮"),
            variant=config.get("variant", "primary"),
            elem_id=config.get("id")
        )
    
    def _create_slider(self, config: Dict) -> gr.Slider:
        """创建滑块组件"""
        return gr.Slider(
            minimum=config.get("minimum", 0),
            maximum=config.get("maximum", 1),
            value=config.get("value", 0.5),
            step=config.get("step", 0.01),
            label=config.get("label", ""),
            elem_id=config.get("id")
        )
    
    def _create_checkbox(self, config: Dict) -> gr.Checkbox:
        """创建复选框组件"""
        return gr.Checkbox(
            label=config.get("label", ""),
            value=config.get("value", False),
            elem_id=config.get("id")
        )
    
    def build_layout(self, components_config: List[Dict], layout_config: Dict):
        """
        构建布局
        
        Args:
            components_config: 组件配置列表
            layout_config: 布局配置
            
        Returns:
            构建好的Gradio组件树和组件字典
        """
        # 保存组件配置供后续使用
        self.components_config_dict = {comp['id']: comp for comp in components_config}
        
        # 根据布局配置组织和创建组件
        layout_type = layout_config.get("type", "two_column")
        
        if layout_type == "two_column":
            return self._build_two_column_layout(layout_config)
        elif layout_type == "tree":
            return self._build_tree_layout(layout_config)
        else:
            raise ValueError(f"未知布局类型: {layout_type}")
    
    def _build_two_column_layout(self, config: Dict):
        """
        构建两栏布局
        
        Args:
            config: {
                "type": "two_column",
                "left": ["gif_box"],
                "right": {...} 或 ["comp1", "comp2"]
            }
        """
        with gr.Row(elem_id=config.get("elem_id", "main_content_row")) as row:
            # 左栏
            left_config = config.get("left", [])
            with gr.Column(scale=config.get("left_scale", 1)):
                self._render_components(left_config)
            
            # 右栏
            right_config = config.get("right", [])
            with gr.Column(scale=config.get("right_scale", 2), elem_id="info_column"):
                self._render_components(right_config)
        
        return row
    
    def _build_tree_layout(self, config: Dict):
        """
        构建树形嵌套布局（递归）
        
        Args:
            config: {
                "type": "tree",
                "children": [
                    {"type": "vstack", "children": [...]},
                    {"type": "hstack", "children": [...]},
                    "component_id"
                ]
            }
        """
        children = config.get("children", [])
        self._render_components(children)
    
    def _render_components(self, items: Union[List, Dict]):
        """
        递归渲染组件（按需创建）
        
        Args:
            items: 可以是：
                - 字符串：组件id
                - 列表：组件id列表或嵌套配置列表
                - 字典：嵌套布局配置
        """
        # 如果是字典，说明是嵌套布局
        if isinstance(items, dict):
            layout_type = items.get("type")
            elem_id = items.get("elem_id")
            children = items.get("children", [])
            
            if layout_type == "vstack":
                # 垂直堆叠（Column）
                with gr.Column(elem_id=elem_id):
                    self._render_components(children)
            
            elif layout_type == "hstack":
                # 水平堆叠（Row）
                with gr.Row(elem_id=elem_id):
                    self._render_components(children)
            
            else:
                # 未知类型，当作组件id处理
                if "id" in items:
                    comp_id = items["id"]
                    self._create_and_store(comp_id)
        
        # 如果是列表，递归处理每个元素
        elif isinstance(items, list):
            for item in items:
                self._render_components(item)
        
        # 如果是字符串，说明是组件id
        elif isinstance(items, str):
            self._create_and_store(items)
    
    def _create_and_store(self, comp_id: str):
        """
        按需创建并存储组件（在当前Gradio上下文中）
        
        Args:
            comp_id: 组件ID
        """
        # 如果已经创建过，不再重复创建
        if comp_id in self.components:
            print(f"⚠️  警告: 组件 '{comp_id}' 已存在，跳过重复创建")
            return
        
        # 从配置中获取组件配置
        comp_config = self.components_config_dict.get(comp_id)
        if not comp_config:
            print(f"⚠️  警告: 未找到组件配置 '{comp_id}'")
            return
        
        # 如果字段有checkbox，需要在Column中包裹
        if comp_config.get("has_checkbox", False) and comp_config.get("type") == "textbox":
            with gr.Column():
                # create_component会返回(textbox, checkbox)元组
                # Gradio会按照创建顺序渲染，所以checkbox会先渲染
                self.create_component(comp_config)
        else:
            # 创建组件（在当前上下文中自动渲染）
            self.create_component(comp_config)
    
    def get_component(self, comp_id: str) -> Union[gr.Component, tuple, None]:
        """获取已创建的组件"""
        return self.components.get(comp_id)
    
    def get_checkbox(self, comp_id: str) -> Union[gr.Checkbox, None]:
        """获取字段对应的checkbox"""
        return self.checkboxes.get(comp_id)
    
    def get_all_components(self) -> Dict[str, Union[gr.Component, tuple]]:
        """获取所有组件"""
        return self.components
    
    def get_all_checkboxes(self) -> Dict[str, gr.Checkbox]:
        """获取所有checkbox"""
        return self.checkboxes

