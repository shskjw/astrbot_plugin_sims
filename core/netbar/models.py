from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


# ========== 网吧电脑配置 ==========
class ComputerConfig(BaseModel):
    """电脑配置"""
    basic: int = 5  # 基础配置数量
    standard: int = 0  # 标准配置数量
    premium: int = 0  # 高端配置数量


# ========== 网吧员工 ==========
class NetbarEmployee(BaseModel):
    """网吧员工"""
    id: str
    position: str  # 收银员/网管/保洁/经理
    salary: int
    skill: int = 5
    satisfaction: int = 100
    experience: int = 0
    work_hours: int = 0
    performance: int = 100
    hire_date: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: str = "在岗"


# ========== 网吧设施 ==========
class NetbarFacilities(BaseModel):
    """网吧设施"""
    air_conditioner: bool = True
    wifi: bool = True
    security_system: bool = True
    snack_bar: bool = False
    rest_area: bool = False
    gaming_area: bool = False


# ========== 网吧环境 ==========
class NetbarEnvironment(BaseModel):
    """网吧环境"""
    temperature: int = 25
    noise: int = 50
    lighting: int = 80
    air_quality: int = 90
    rating: int = 85


# ========== 网吧维护 ==========
class NetbarMaintenance(BaseModel):
    """网吧维护"""
    status: int = 100  # 维护状态百分比
    last_maintenance: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_cost: int = 0


# ========== 网吧统计 ==========
class NetbarStatistics(BaseModel):
    """网吧统计数据"""
    total_customers: int = 0
    current_customers: int = 0
    average_rating: float = 4.5
    member_satisfaction: int = 85
    service_quality: int = 80
    basic_usage: float = 0.6
    standard_usage: float = 0
    premium_usage: float = 0


# ========== 网吧会员 ==========
class NetbarMembers(BaseModel):
    """网吧会员统计"""
    normal: int = 0
    silver: int = 0
    gold: int = 0
    diamond: int = 0


# ========== 网吧完整信息 ==========
class NetbarInfo(BaseModel):
    """网吧完整信息"""
    id: str
    owner_id: str
    name: str = "我的网吧"
    level: int = 1
    experience: int = 0
    computers: ComputerConfig = Field(default_factory=ComputerConfig)
    staff: List[NetbarEmployee] = Field(default_factory=list)
    cleanliness: int = 100
    reputation: int = 50
    members: NetbarMembers = Field(default_factory=NetbarMembers)
    income: int = 0
    expenses: int = 0
    daily_income: int = 0
    daily_expenses: int = 0
    last_update: str = Field(default_factory=lambda: datetime.now().isoformat())
    facilities: NetbarFacilities = Field(default_factory=NetbarFacilities)
    environment: NetbarEnvironment = Field(default_factory=NetbarEnvironment)
    maintenance: NetbarMaintenance = Field(default_factory=NetbarMaintenance)
    statistics: NetbarStatistics = Field(default_factory=NetbarStatistics)
    credit_points: int = 100


# ========== 员工类型配置 ==========
STAFF_TYPES = {
    "收银员": {
        "salary": 3000,
        "skill": 5,
        "description": "负责收银和客户接待",
        "requirements": "基础服务技能"
    },
    "网管": {
        "salary": 4000,
        "skill": 7,
        "description": "负责设备维护和技术支持",
        "requirements": "计算机维护经验"
    },
    "保洁": {
        "salary": 2500,
        "skill": 3,
        "description": "负责环境卫生维护",
        "requirements": "认真负责"
    },
    "经理": {
        "salary": 6000,
        "skill": 10,
        "description": "负责网吧整体运营",
        "requirements": "3年以上管理经验"
    }
}


# ========== 设备类型配置 ==========
COMPUTER_TYPES = {
    "基础": {
        "key": "basic",
        "price": 3000,
        "performance": 5,
        "maintenance_cost": 80,
        "description": "适合网页浏览和办公"
    },
    "标准": {
        "key": "standard",
        "price": 5000,
        "performance": 8,
        "maintenance_cost": 120,
        "description": "满足主流游戏需求"
    },
    "高端": {
        "key": "premium",
        "price": 8000,
        "performance": 12,
        "maintenance_cost": 200,
        "description": "支持高端游戏和专业应用"
    }
}


# ========== 设施配置 ==========
FACILITY_TYPES = {
    "小卖部": {
        "key": "snack_bar",
        "price": 10000,
        "daily_income": 500,
        "description": "销售零食饮料"
    },
    "休息区": {
        "key": "rest_area",
        "price": 15000,
        "reputation_bonus": 10,
        "description": "提供舒适的休息环境"
    },
    "电竞区": {
        "key": "gaming_area",
        "price": 30000,
        "reputation_bonus": 20,
        "premium_bonus": 5,
        "description": "专业电竞设备区域"
    }
}


# ========== 旧版兼容模型 ==========
class NetbarUser(BaseModel):
    """网吧用户（兼容旧版）"""
    user_id: str
    balance: int = 0
    vip_until: int = 0
    rented_until: int = 0
    hours_remaining: int = 0


class NetbarItem(BaseModel):
    """网吧物品（兼容旧版）"""
    id: str
    name: str
    price: int
    stock: int = 0


# ========== 排行榜条目 ==========
class NetbarRankingEntry(BaseModel):
    """网吧排行榜条目"""
    owner_id: str
    owner_name: str
    netbar_name: str
    level: int
    reputation: int
    total_income: int
    computer_count: int
