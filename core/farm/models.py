from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Plot(BaseModel):
    crop: Optional[str] = None
    plantedAt: Optional[str] = None
    water: int = 0
    fertility: int = 0
    health: int = 100
    growthStage: int = 0
    harvestReady: bool = False

class Land(BaseModel):
    level: int
    name: str
    size: int
    plots: List[Plot]
    waterRetention: int = 1
    fertilityBonus: int = 1

class Inventory(BaseModel):
    seeds: List[dict] = Field(default_factory=list)
    crops: List[dict] = Field(default_factory=list)
    tools: List[dict] = Field(default_factory=list)

class Statistics(BaseModel):
    totalHarvested: int = 0
    totalIncome: int = 0
    plantsGrown: int = 0
    timeSpent: int = 0

class FarmData(BaseModel):
    name: str
    level: int = 1
    experience: int = 0
    createdAt: str
    lastUpdate: str
    land: Land
    inventory: Inventory
    statistics: Statistics
    log: List[dict] = Field(default_factory=list)
    activeEvents: List[dict] = Field(default_factory=list)

# ========== 农场事件系统 ==========

class FarmEventEffect(BaseModel):
    """事件效果"""
    water: int = 0           # 水分变化
    growth: int = 0          # 生长速度变化
    health: int = 0          # 健康度变化
    yield_bonus: int = 0     # 产量变化
    fertility: int = 0       # 肥力变化
    quality: int = 0         # 品质变化

class FarmEvent(BaseModel):
    """农场随机事件配置"""
    id: int
    name: str
    type: str                # weather/pest/soil/disaster/blessing
    effect: FarmEventEffect
    description: str
    probability: int = 10    # 发生概率(百分比)
    duration: int = 1        # 持续天数
    remedy: Optional[str] = None  # 补救道具
    icon: str = "default_event.png"

class ActiveFarmEvent(BaseModel):
    """激活的农场事件"""
    event_id: int
    event_name: str
    event_type: str
    effect: Dict[str, Any]
    started_at: str
    expires_at: str
    remedied: bool = False   # 是否已补救

# ========== 季节系统 ==========

class SeasonEffect(BaseModel):
    """季节效果"""
    growth: float = 1.0      # 生长速度倍率
    water: float = 1.0       # 水分消耗倍率
    temperature: str = "适中"

class Season(BaseModel):
    """季节配置"""
    id: int
    name: str                # 春季/夏季/秋季/冬季
    months: List[int]        # 包含的月份
    description: str
    effects: SeasonEffect
    special: str = ""        # 特殊说明
    recommended_crops: List[str] = Field(default_factory=list)

# ========== 农场排行榜 ==========

class FarmRankingEntry(BaseModel):
    """排行榜条目"""
    user_id: str
    farm_name: str
    level: int
    experience: int
    total_harvested: int
    total_income: int

# ========== 出售农产品 ==========

class CropSaleRecord(BaseModel):
    """农产品出售记录"""
    user_id: str
    crop_name: str
    quantity: int
    price_per_unit: int
    total_price: int
    sold_at: str
