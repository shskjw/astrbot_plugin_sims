"""
数据管理器 - 使用 JSON 文件存储，支持异步操作防止框架卡死

Redis 为可选功能，可在配置中启用
"""
from pathlib import Path
import json
import asyncio
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

try:
    import aiofiles
    _AIOFILES_AVAILABLE = True
except ImportError:
    _AIOFILES_AVAILABLE = False

try:
    from astrbot.core.utils.astrbot_path import get_astrbot_data_path
    _ASTRBOT_PATH_AVAILABLE = True
except ImportError:
    _ASTRBOT_PATH_AVAILABLE = False

# 插件名称
PLUGIN_NAME = "astrbot_plugin_sims"

# 线程池用于异步文件操作（防止阻塞事件循环）
_executor = ThreadPoolExecutor(max_workers=2)


class DataManager:
    """
    数据管理器 - JSON 文件存储
    
    使用 AstrBot 规范路径: plugin_data/{plugin_name}/
    支持异步操作防止框架卡死
    
    用法:
        dm = DataManager()
        # 同步方法（简单场景）
        dm.save_user('123', {'name': 'abc'})
        user = dm.load_user('123')
        
        # 异步方法（推荐，防止阻塞）
        user = await dm.async_load_user('123')
        await dm.async_save_user('123', user)
    """

    def __init__(self, base_path: Optional[Path] = None, plugin_name: str = None):
        # 确定数据根目录
        if base_path:
            self.root = Path(base_path)
        elif _ASTRBOT_PATH_AVAILABLE:
            # 使用 AstrBot 规范路径
            self.root = Path(get_astrbot_data_path()) / "plugin_data" / (plugin_name or PLUGIN_NAME)
        else:
            # 回退到插件目录下的 data
            self.root = Path(__file__).resolve().parents[2] / "data"
        
        # 确保目录存在
        self.root.mkdir(parents=True, exist_ok=True)
        self.users_dir = self.root / "users"
        self.users_dir.mkdir(parents=True, exist_ok=True)

    # ========== 同步方法（简单场景使用） ==========
    def load_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """同步加载用户数据"""
        p = self.users_dir / f"{user_id}.json"
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_user(self, user_id: str, data: Dict[str, Any]):
        """同步保存用户数据"""
        p = self.users_dir / f"{user_id}.json"
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ========== 异步方法（推荐使用，防止框架卡死） ==========
    async def async_load_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """异步加载用户数据"""
        p = self.users_dir / f"{user_id}.json"
        if not p.exists():
            return None
        
        try:
            if _AIOFILES_AVAILABLE:
                async with aiofiles.open(p, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            else:
                # 使用线程池避免阻塞
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    _executor,
                    lambda: json.loads(p.read_text(encoding='utf-8'))
                )
        except Exception:
            return None

    async def async_save_user(self, user_id: str, data: Dict[str, Any]):
        """异步保存用户数据"""
        p = self.users_dir / f"{user_id}.json"
        content = json.dumps(data, ensure_ascii=False, indent=2)
        
        try:
            if _AIOFILES_AVAILABLE:
                async with aiofiles.open(p, 'w', encoding='utf-8') as f:
                    await f.write(content)
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    _executor,
                    lambda: p.write_text(content, encoding='utf-8')
                )
        except Exception as e:
            raise RuntimeError(f"保存用户数据失败: {e}")

    async def async_load_json(self, filename: str) -> Dict[str, Any]:
        """异步加载任意 JSON 文件"""
        p = self.root / filename
        if not p.exists():
            return {}
        try:
            if _AIOFILES_AVAILABLE:
                async with aiofiles.open(p, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            else:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    _executor,
                    lambda: json.loads(p.read_text(encoding='utf-8'))
                )
        except Exception:
            return {}

    async def async_save_json(self, filename: str, data: Dict[str, Any]):
        """异步保存任意 JSON 文件"""
        p = self.root / filename
        content = json.dumps(data, ensure_ascii=False, indent=2)
        try:
            if _AIOFILES_AVAILABLE:
                async with aiofiles.open(p, 'w', encoding='utf-8') as f:
                    await f.write(content)
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    _executor,
                    lambda: p.write_text(content, encoding='utf-8')
                )
        except Exception as e:
            raise RuntimeError(f"保存 JSON 失败: {e}")

    # ========== 封禁系统 ==========
    def set_ban(self, user_id: str, until_ts: int):
        """设置用户封禁"""
        bans = self._read_json(self.root / "bans.json")
        bans[user_id] = until_ts
        (self.root / "bans.json").write_text(json.dumps(bans, indent=2), encoding="utf-8")

    def get_ban(self, user_id: str) -> Optional[int]:
        """获取用户封禁状态"""
        bans = self._read_json(self.root / "bans.json")
        return bans.get(user_id)

    def list_users(self) -> list:
        """列出所有用户ID"""
        return [p.stem for p in self.users_dir.glob("*.json")]

    # ========== 内部方法 ==========
    def _read_json(self, path: Path) -> Dict[str, Any]:
        """读取 JSON 文件"""
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def get_data_path(self) -> Path:
        """获取数据根目录"""
        return self.root
