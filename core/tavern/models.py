from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

# 饮品数据模型
class Drink(BaseModel):
    id: str
    name: str
    type: str  # beer, wine, spirits, mixed, special
    base_price: int
    description: str
    ingredients: List[str]
    popularity: int = 50  # 1-100
    alcohol_content: str
    preparation_time: str  # 短, 中, 长
    special_effects: List[str] = []
    sales: int = 0  # 总销售量

# 市场物资模型
class MarketItem(BaseModel):
    id: str
    name: str
    type: str  # beer, wine, spirits
    description: str
    price: int
    quantity: int  # 市场库存
    quality: int  # 品质等级 1-3

# 员工模型
class Staff(BaseModel):
    id: str
    name: str
    staff_type: str  # bartender, waiter, cleaner, security, musician
    salary: int
    level: int = 1
    experience: int = 0
    hired_at: str
    skills: List[Dict[str, str]] = []

# 用户酒馆物资库存
class TavernSupplies(BaseModel):
    beer_basic: int = 0
    beer_craft: int = 0
    beer_premium: int = 0
    wine_table: int = 0
    wine_vintage: int = 0
    wine_premium: int = 0
    spirits_vodka: int = 0
    spirits_whiskey: int = 0
    special_fruit: int = 0
    special_honey: int = 0

# 酒馆事件模型
class TavernEvent(BaseModel):
    id: str
    name: str
    description: str
    probability: float
    impact: Dict[str, int]
    choices: List[Dict] = []

# 用户制作的饮品库存
class UserDrink(BaseModel):
    id: str
    drink_id: str
    drink_name: str
    quality: int
    created_at: str
    count: int = 1

# 用户酒馆信息
class TavernData(BaseModel):
    user_id: str
    name: str
    level: int = 1
    popularity: int = 10  # 人气 1-100
    capacity: int = 20  # 容量（每天最多接待人数）
    cleanliness: int = 100  # 清洁度 0-100
    atmosphere: int = 50  # 氛围 0-100
    reputation: int = 3  # 声誉 1-10
    customer_satisfaction: int = 80  # 顾客满意度
    
    # 库存和菜单
    drinks: List[UserDrink] = []  # 制作好的饮品
    custom_menu: List[Dict] = []  # 自定义菜单（可修改价格）
    supplies: TavernSupplies = TavernSupplies()
    
    # 员工
    staff: List[Staff] = []
    staff_bonuses: Dict[str, float] = {}  # 员工加成
    
    # 运营数据
    daily_income: int = 0
    total_income: int = 0
    last_operated: Optional[str] = None
    created_at: str
    
    # 事件
    special_events: List[Dict] = []

# 用户数据扩展（包含酒馆信息）
class UserTavernProfile(BaseModel):
    user_id: str
    has_tavern: bool = False
    tavern: Optional[TavernData] = None


# ========== 高级功能模型 ==========

# 酒馆事件选择
class EventChoice(BaseModel):
    text: str
    effects: Dict[str, int] = {}
    requirements: Dict = {}

# 完整事件模型
class TavernEventFull(BaseModel):
    id: str
    title: str
    description: str
    type: str  # positive, negative, neutral
    frequency: int  # 触发概率权重
    min_level: int = 1
    choices: List[EventChoice] = []

# 事件处理结果
class EventResult(BaseModel):
    event_id: str
    event_title: str
    description: str
    choice_made: str
    effects_applied: Dict[str, int]
    special_reward: Optional[str] = None

# 酒馆排行榜条目
class TavernRankEntry(BaseModel):
    user_id: str
    tavern_name: str
    level: int
    total_income: int
    reputation: int
    staff_count: int
    rank_score: int  # 综合评分

# 参观记录
class VisitRecord(BaseModel):
    visitor_id: str
    visited_at: str
    rating: int  # 评分 1-5
    comment: Optional[str] = None


# ========== 特殊活动模型 ==========

class TavernActivity(BaseModel):
    """酒馆特殊活动"""
    id: str
    name: str
    type: str  # happy_hour, live_music, theme_night, tasting_event, competition
    description: str
    duration_hours: int = 4
    cost: int  # 举办费用
    min_level: int = 1
    effects: Dict[str, int] = {}  # 活动期间的效果加成
    requirements: Dict = {}  # 举办需求（员工、物资等）


class ActiveTavernActivity(BaseModel):
    """正在进行的活动"""
    activity_id: str
    activity_name: str
    host_id: str  # 举办者
    start_time: str
    end_time: str
    participants: List[str] = []  # 参与者ID
    bonus_earned: int = 0  # 活动期间额外收益


# ========== 合作酿酒模型 ==========

class BrewingProject(BaseModel):
    """合作酿酒项目"""
    id: str
    name: str  # 酒的名字
    initiator_id: str
    participants: Dict[str, dict]  # {user_id: {contributed, materials}}
    recipe_type: str  # beer, wine, spirits
    quality: int = 50
    progress: int = 0  # 0-100
    status: str = "brewing"  # brewing/completed/failed
    created_time: str
    estimated_complete: str
