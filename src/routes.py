"""
路由配置：定义任务映射

目前支持多个任务，可以轻松添加更多
"""

ROUTES = [
    {
        "url": "/annotation",
        "task": "annotation",
        "port": 7800,
        "description": "物体属性标注"
    },
    {
        "url": "/whole_annotation",
        "task": "whole_annotation",
        "port": 7801,
        "description": "整体物体标注"
    },
    {
        "url": "/part_annotation",
        "task": "part_annotation",
        "port": 7802,
        "description": "部件标注"
    },
    # 以后添加新任务：
    # {
    #     "url": "/review",
    #     "task": "review",
    #     "port": 7803,
    #     "description": "质量审核"
    # },
]

DEFAULT_PORT = 7800

