from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


# ========== 鱼类模型 ==========
class Fish(BaseModel):
    """鱼类信息"""
    id: str
    name: str
    rarity: int = 1  # 1-5 稀有度
    price: int = 10  # 基础价格
    weight_min: float = 0.5  # 最小重量(kg)
    weight_max: float = 2.0  # 最大重量(kg)
    exp: int = 10  # 获得经验
    difficulty: int = 1  # 所需钓鱼等级
    freshness: int = 3600  # 保鲜时间(秒)
    description: str = ""


# ========== 钓鱼装备 ==========
class FishingRod(BaseModel):
    """鱼竿"""
    id: str
    name: str
    level: int = 1
    success_rate: int = 50  # 成功率
    price: int = 0
    upgrade_cost: Optional[int] = None
    description: str = ""


class FishingBait(BaseModel):
    """鱼饵"""
    id: str
    name: str
    level: int = 1
    attract_rate: int = 50  # 吸引率
    price: int = 0
    upgrade_cost: Optional[int] = None
    description: str = ""


class FishBasket(BaseModel):
    """鱼篓"""
    id: str
    name: str
    capacity: int = 10  # 容量
    price: int = 0
    description: str = ""


# ========== 钓到的鱼 ==========
class CaughtFish(BaseModel):
    """钓到的鱼"""
    fish_id: str
    weight: float
    catch_time: str  # ISO时间戳
    price: int = 0  # 计算后的价格


# ========== 用户钓鱼数据 ==========
class FishingUserData(BaseModel):
    """用户钓鱼数据"""
    user_id: str
    rod: str = "rod_01"  # 当前鱼竿ID
    bait: str = "bait_01"  # 当前鱼饵ID
    basket: str = "basket_01"  # 当前鱼篓ID
    fishing_status: str = "idle"  # idle/waiting/ready
    start_time: float = 0  # 开始时间戳
    fish_basket: List[CaughtFish] = Field(default_factory=list)  # 鱼篓中的鱼
    total_catch: int = 0  # 总钓鱼数
    total_weight: float = 0  # 总重量
    exp: int = 0  # 当前经验
    level: int = 1  # 钓鱼等级


# ========== 钓鱼结果 ==========
class FishingResult(BaseModel):
    """钓鱼结果"""
    success: bool
    fish: Optional[Fish] = None
    weight: float = 0
    exp_gained: int = 0
    level_up: bool = False
    new_level: int = 0
    message: str = ""


# ========== 出售结果 ==========
class SellResult(BaseModel):
    """出售结果"""
    total_price: int
    fish_count: int
    spoiled_count: int
    message: str = ""


# ========== 排行榜条目 ==========
class FishingRankingEntry(BaseModel):
    """钓鱼排行榜条目"""
    user_id: str
    user_name: str
    level: int
    total_catch: int
    total_weight: float
    best_catch_fish: Optional[str] = None
    best_catch_weight: float = 0


# ========== 装备商店 ==========
class EquipmentShopItem(BaseModel):
    """装备商店物品"""
    id: str
    name: str
    type: str  # rod/bait/basket
    price: int
    description: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
