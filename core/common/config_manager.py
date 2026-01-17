"""
配置管理器 - 读取和管理插件配置
"""
from typing import Any, Dict, Optional


class ConfigManager:
    """
    配置管理器
    
    用于读取 AstrBot 传入的配置或使用默认配置
    AstrBot 配置格式为扁平结构: {"key": value, ...}
    """
    
    # 默认配置（扁平结构，与 _conf_schema.json 对应）
    DEFAULT_CONFIG = {
        "initial_coins": 1000,
        "daily_sign_reward": 100,
        "sign_cooldown": 86400,
        "farm_enabled": True,
        "farm_create_cost": 500,
        "police_enabled": True,
        "doctor_enabled": True,
        "firefighter_enabled": True,
        "fishing_enabled": True,
        "netbar_enabled": True,
        "cinema_enabled": True,
        "chef_enabled": True,
        "tavern_enabled": True,
        "stock_enabled": True,
        "anti_cheat_enabled": True,
        "max_daily_transactions": 100,
    }
    
    _instance: Optional['ConfigManager'] = None
    _config: Dict[str, Any] = {}
    _admins: list = []
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = cls.DEFAULT_CONFIG.copy()
            cls._instance._admins = []
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """获取配置管理器实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_config(self, config: Dict[str, Any]) -> None:
        """
        加载配置
        
        Args:
            config: AstrBot 传入的配置字典（扁平结构）
        """
        if config:
            self._config.update(config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        return self._config.get(key, default)
    
    def is_system_enabled(self, system: str) -> bool:
        """
        检查系统是否启用
        
        Args:
            system: 系统名称，如 "farm", "police"
            
        Returns:
            是否启用
        """
        key = f"{system}_enabled"
        return self._config.get(key, True)
    
    def is_admin(self, user_id: str) -> bool:
        """
        检查是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否为管理员
        """
        return str(user_id) in [str(a) for a in self._admins]
    
    def set_admins(self, admins: list) -> None:
        """
        设置管理员列表
        
        Args:
            admins: 管理员ID列表
        """
        self._admins = [str(a) for a in admins if str(a).isdigit()]
    
    @property
    def initial_coins(self) -> int:
        """获取初始金币数"""
        return self._config.get("initial_coins", 1000)
    
    @property
    def daily_sign_reward(self) -> int:
        """获取签到奖励"""
        return self._config.get("daily_sign_reward", 100)
    
    @property
    def sign_cooldown(self) -> int:
        """获取签到冷却时间"""
        return self._config.get("sign_cooldown", 86400)


# 全局配置实例
config = ConfigManager.get_instance()


def get_config() -> ConfigManager:
    """获取配置管理器"""
    return config
