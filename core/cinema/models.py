from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


# ========== 影厅 ==========
class Theater(BaseModel):
    """影厅"""
    id: str
    name: str
    type: str  # small/medium/large/vip
    capacity: int = 100
    maintenance_cost: int = 1000
    current_movie: Optional[str] = None
    schedule: List[dict] = Field(default_factory=list)


# ========== 电影 ==========
class Movie(BaseModel):
    """电影"""
    id: str
    title: str
    genre: str  # action/comedy/romance/sci-fi/horror
    duration: int = 120  # 分钟
    base_price: int = 50
    popularity: int = 70
    rating: float = 8.0
    cost: int = 50000  # 购买版权费用
    revenue: int = 0  # 累计收入
    viewers: int = 0  # 累计观众
    purchase_date: str = Field(default_factory=lambda: datetime.now().isoformat())


# ========== 设施 ==========
class Facility(BaseModel):
    """电影院设施"""
    type: str  # snack_bar/drink_bar/restaurant/gift_shop
    name: str
    maintenance_cost: int
    revenue_multiplier: float = 1.2


# ========== 员工 ==========
class CinemaStaff(BaseModel):
    """电影院员工"""
    id: str
    type: str  # ticket_seller/usher/cleaner/manager
    name: str
    level: int = 1
    efficiency: float = 1.0
    salary: int = 3000
    hire_date: str = Field(default_factory=lambda: datetime.now().isoformat())


# ========== 排片 ==========
class ScheduleItem(BaseModel):
    """排片信息"""
    movie_id: str
    movie_title: str
    theater_id: str
    time: str  # 24小时制 如 14:30
    duration: int
    price: int


# ========== 电影院完整信息 ==========
class CinemaInfo(BaseModel):
    """电影院完整信息"""
    id: str
    owner_id: str
    name: str = "我的电影院"
    level: int = 1
    theaters: List[Theater] = Field(default_factory=list)
    movies: List[Movie] = Field(default_factory=list)
    facilities: List[Facility] = Field(default_factory=list)
    staff: List[CinemaStaff] = Field(default_factory=list)
    daily_revenue: int = 0
    total_revenue: int = 0
    reputation: int = 50
    maintenance_cost: int = 0
    staff_cost: int = 0
    last_update: str = Field(default_factory=lambda: datetime.now().isoformat())


# ========== 影厅类型配置 ==========
THEATER_TYPES = {
    "small": {
        "name": "小型影厅",
        "capacity": 100,
        "cost": 50000,
        "maintenance_cost": 1000,
        "next_level": "medium",
        "upgrade_cost": 30000
    },
    "medium": {
        "name": "中型影厅",
        "capacity": 200,
        "cost": 100000,
        "maintenance_cost": 2000,
        "next_level": "large",
        "upgrade_cost": 80000
    },
    "large": {
        "name": "大型影厅",
        "capacity": 300,
        "cost": 200000,
        "maintenance_cost": 3000,
        "next_level": "vip",
        "upgrade_cost": 150000
    },
    "vip": {
        "name": "VIP影厅",
        "capacity": 50,
        "cost": 300000,
        "maintenance_cost": 5000,
        "next_level": None,
        "upgrade_cost": 0
    }
}


# ========== 设施类型配置 ==========
FACILITY_TYPES = {
    "snack_bar": {
        "name": "零食店",
        "cost": 10000,
        "maintenance_cost": 500,
        "revenue_multiplier": 1.2,
        "description": "销售爆米花、薯片等零食"
    },
    "drink_bar": {
        "name": "饮品店",
        "cost": 15000,
        "maintenance_cost": 800,
        "revenue_multiplier": 1.3,
        "description": "销售各类饮料和奶茶"
    },
    "restaurant": {
        "name": "餐厅",
        "cost": 30000,
        "maintenance_cost": 1500,
        "revenue_multiplier": 1.5,
        "description": "提供正餐和简餐"
    },
    "gift_shop": {
        "name": "礼品店",
        "cost": 20000,
        "maintenance_cost": 1000,
        "revenue_multiplier": 1.4,
        "description": "销售电影周边和纪念品"
    }
}


# ========== 员工类型配置 ==========
STAFF_TYPES = {
    "ticket_seller": {
        "name": "售票员",
        "salary": 3000,
        "efficiency": 1.0,
        "training_cost": 1000,
        "max_level": 5,
        "description": "负责售票和咨询服务"
    },
    "usher": {
        "name": "引座员",
        "salary": 2500,
        "efficiency": 1.0,
        "training_cost": 800,
        "max_level": 5,
        "description": "负责引导观众入座"
    },
    "cleaner": {
        "name": "清洁工",
        "salary": 2000,
        "efficiency": 1.0,
        "training_cost": 500,
        "max_level": 5,
        "description": "负责影院卫生维护"
    },
    "manager": {
        "name": "经理",
        "salary": 5000,
        "efficiency": 1.5,
        "training_cost": 2000,
        "max_level": 5,
        "description": "负责整体运营管理"
    }
}


# ========== 电影类型配置 ==========
MOVIE_GENRES = {
    "action": {
        "name": "动作片",
        "base_price": 50,
        "popularity": 70,
        "duration": 120,
        "cost": 80000
    },
    "comedy": {
        "name": "喜剧片",
        "base_price": 45,
        "popularity": 75,
        "duration": 100,
        "cost": 50000
    },
    "romance": {
        "name": "爱情片",
        "base_price": 40,
        "popularity": 80,
        "duration": 110,
        "cost": 40000
    },
    "sci_fi": {
        "name": "科幻片",
        "base_price": 55,
        "popularity": 65,
        "duration": 140,
        "cost": 100000
    },
    "horror": {
        "name": "恐怖片",
        "base_price": 45,
        "popularity": 60,
        "duration": 95,
        "cost": 35000
    }
}


# ========== 可购买的电影列表 ==========
AVAILABLE_MOVIES = {
    "action": [
        {"id": "ACT001", "title": "疾速追杀", "rating": 8.5, "popularity": 85},
        {"id": "ACT002", "title": "谍影重重", "rating": 8.2, "popularity": 80},
        {"id": "ACT003", "title": "碟中谍", "rating": 8.8, "popularity": 90},
    ],
    "comedy": [
        {"id": "COM001", "title": "夏洛特烦恼", "rating": 8.0, "popularity": 88},
        {"id": "COM002", "title": "人在囧途", "rating": 7.8, "popularity": 82},
        {"id": "COM003", "title": "唐人街探案", "rating": 8.3, "popularity": 85},
    ],
    "romance": [
        {"id": "ROM001", "title": "那些年", "rating": 8.1, "popularity": 82},
        {"id": "ROM002", "title": "泰坦尼克号", "rating": 9.0, "popularity": 95},
        {"id": "ROM003", "title": "怦然心动", "rating": 8.8, "popularity": 88},
    ],
    "sci_fi": [
        {"id": "SCI001", "title": "星际穿越", "rating": 9.3, "popularity": 92},
        {"id": "SCI002", "title": "流浪地球", "rating": 8.5, "popularity": 90},
        {"id": "SCI003", "title": "盗梦空间", "rating": 9.2, "popularity": 88},
    ],
    "horror": [
        {"id": "HOR001", "title": "招魂", "rating": 7.5, "popularity": 70},
        {"id": "HOR002", "title": "寂静之地", "rating": 7.8, "popularity": 72},
        {"id": "HOR003", "title": "闪灵", "rating": 8.0, "popularity": 68},
    ]
}


# ========== 排行榜条目 ==========
class CinemaRankingEntry(BaseModel):
    """电影院排行榜条目"""
    owner_id: str
    owner_name: str
    cinema_name: str
    total_revenue: int
    reputation: int
    theater_count: int
    movie_count: int
