from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

class Recipe(BaseModel):
    """食谱数据模型"""
    id: str
    name: str
    category: str  # 汤类、炒菜、甜点、主食等
    difficulty: int  # 难度 1-5
    time: int  # 烹饪时间（秒）
    exp: int  # 成功制作获得经验
    unlock_level: int  # 解锁需要的等级
    ingredients: List[Dict[str, Any]]  # 所需食材
    steps: List[str]  # 烹饪步骤
    description: str
    success_rate: int  # 基础成功率
    base_price: int  # 基础售价
    nutrition: Dict[str, int]  # 营养属性 {hunger, mood, energy}


class Ingredient(BaseModel):
    """食材数据模型"""
    id: str
    name: str
    category: str
    price: int  # 购买价格
    rarity: str  # 稀有度 common/uncommon/rare
    description: str


class Kitchenware(BaseModel):
    """厨具数据模型"""
    id: str
    name: str
    category: str
    price: int
    unlock_level: int
    description: str
    success_rate_bonus: int  # 成功率加成
    quality_bonus: int  # 品质加成
    time_reduction: int  # 时间减少（秒）


class Dish(BaseModel):
    """制作好的料理"""
    id: str  # 唯一ID
    recipe_id: str
    name: str
    quality: int  # 品质（影响出售价格和效果）
    created_time: str
    nutrition: Dict[str, int]
    base_price: int


class ChefData(BaseModel):
    """厨师角色数据"""
    user_id: str
    level: int = 1
    experience: int = 0
    recipes_known: List[str] = Field(default_factory=lambda: ["soup_01"])  # 默认解锁番茄蛋汤
    success_count: int = 0  # 成功次数
    total_count: int = 0  # 总尝试次数
    reputation: int = 50  # 声望（影响售价）
    created_time: str = Field(default_factory=lambda: datetime.now().isoformat())


class Team(BaseModel):
    """厨师团队"""
    id: str
    name: str
    leader_id: str
    members: List[str]  # 成员ID列表
    level: int = 1
    funds: int = 0  # 团队资金
    created_time: str


class Contest(BaseModel):
    """烹饪竞赛"""
    id: str
    name: str
    creator_id: str
    participants: Dict[str, dict]  # {user_id: {score, dish_id, ...}}
    status: str  # active/finished
    created_time: str
    finished_time: Optional[str] = None


class MarketListing(BaseModel):
    """食材市场挂单"""
    id: str
    seller_id: str
    ingredient_id: str
    ingredient_name: str
    quantity: int
    price_per_unit: int
    created_time: str


class CoopCooking(BaseModel):
    """合作料理"""
    id: str
    recipe_id: str
    recipe_name: str
    initiator_id: str  # 发起者
    participants: Dict[str, dict]  # {user_id: {joined, contributed, ingredients}}
    quality_bonus: int = 0  # 品质加成
    status: str = "preparing"  # preparing/ready/completed/failed
    created_time: str
    completed_time: Optional[str] = None


class Achievement(BaseModel):
    """厨师成就"""
    id: str
    name: str
    description: str
    category: str  # cooking, collection, social, special
    requirement_type: str  # count, level, recipe, reputation
    requirement_value: int
    reward_money: int = 0
    reward_exp: int = 0
    reward_reputation: int = 0
    reward_title: Optional[str] = None


class ChefTitle(BaseModel):
    """厨师称号"""
    id: str
    name: str
    description: str
    unlock_achievement: str  # 解锁所需成就ID
