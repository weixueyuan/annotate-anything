"""
用户认证处理器（基于JSON配置文件）
支持管理员和普通用户两种权限
"""
import json
import sys
from pathlib import Path
from typing import Dict, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class AuthHandler:
    """用户认证处理类（基于JSON配置文件）"""
    
    def __init__(self):
        """初始化认证处理器，加载配置文件"""
        self.config_dir = project_root / "config"
        self.admin_config_path = self.config_dir / "admin_config.jsonl"
        self.user_config_path = self.config_dir / "user_config.jsonl"
        
        # 加载用户配置
        self.admin_users = self._load_config(self.admin_config_path)
        self.user_users = self._load_config(self.user_config_path)
        
        print(f"✓ 加载管理员账号: {len(self.admin_users)} 个")
        print(f"✓ 加载普通用户账号: {len(self.user_users)} 个")
    
    def _load_config(self, config_path: Path) -> list:
        """加载JSONL配置文件（每行一个JSON对象）"""
        if not config_path.exists():
            print(f"⚠️  警告：配置文件不存在: {config_path}")
            return []
        
        users = []
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:  # 跳过空行
                        continue
                    try:
                        user = json.loads(line)
                        # 验证必需字段
                        if 'username' in user and 'password' in user:
                            users.append(user)
                        else:
                            print(f"⚠️  警告：第 {line_num} 行缺少必需字段 (username/password)")
                    except json.JSONDecodeError as e:
                        print(f"❌ 第 {line_num} 行JSON格式错误: {e}")
        except Exception as e:
            print(f"❌ 加载配置文件失败 {config_path}: {e}")
        
        return users
    
    def _verify_user(self, username: str, password: str, is_admin: bool = False) -> Optional[Dict]:
        """验证用户账号和密码"""
        user_list = self.admin_users if is_admin else self.user_users
        
        for user in user_list:
            if user.get('username') == username and user.get('password') == password:
                return user
        return None
    
    def login(self, username: str, password: str) -> Dict:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            {"success": bool, "message": str, "user": dict or None}
            user 包含: username, name, role (admin/annotator)
        """
        if not username or not password:
            return {"success": False, "message": "请输入用户名和密码", "user": None}
        
        username = username.strip()
        password = password.strip()
        
        # 先检查管理员账号
        admin_user = self._verify_user(username, password, is_admin=True)
        if admin_user:
            return {
                "success": True,
                "message": "登录成功！",
                "user": {
                    "username": admin_user.get('username'),
                    "role": "admin"
                }
            }
        
        # 再检查普通用户账号
        user_info = self._verify_user(username, password, is_admin=False)
        if user_info:
            return {
                "success": True,
                "message": "登录成功！",
                "user": {
                    "username": user_info.get('username'),
                    "role": "annotator"
                }
            }
        
        # 验证失败
        return {"success": False, "message": "用户名或密码错误", "user": None}

