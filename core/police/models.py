from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class PoliceSkills(BaseModel):
    """警察技能"""
    investigation: int = 1   # 调查能力
    combat: int = 1          # 战斗能力
    leadership: int = 1      # 领导能力
    communication: int = 1   # 沟通能力

class PoliceInfo(BaseModel):
    rank: str = "实习警员"
    experience: int = 0
    cases_solved: int = 0
    patrol_hours: int = 0
    reputation: int = 50
    stamina: int = 100
    salary: int = 3000
    skills: PoliceSkills = Field(default_factory=PoliceSkills)

class Case(BaseModel):
    id: str
    title: str
    description: str
    reward: int = 0
    type: str = "普通"       # 普通/盗窃/暴力/诈骗
    difficulty: str = "简单"  # 简单/普通/困难/专家
    accepted_by: Optional[str] = None
    created_at: Optional[str] = None

class PoliceEquipment(BaseModel):
    """警察装备"""
    name: str
    type: str                # 武器/防具/工具/特殊
    price: int
    durability: int = 100
    stats: Dict[str, Any] = Field(default_factory=dict)
    maintenance_cost: int = 100

class PoliceUser(BaseModel):
    user_id: str
    info: PoliceInfo = Field(default_factory=PoliceInfo)
    equipment: List[Dict[str, Any]] = Field(default_factory=list)
    assigned_cases: List[str] = Field(default_factory=list)
    current_case: Optional[Dict[str, Any]] = None
    pending_cases: List[Dict[str, Any]] = Field(default_factory=list)

# ========== 警察职级配置 ==========

POLICE_RANKS = {
    "实习警员": {"salary": 3000, "requiredExp": 0, "level": 1},
    "初级警员": {"salary": 5000, "requiredExp": 1000, "level": 2},
    "中级警员": {"salary": 8000, "requiredExp": 3000, "level": 3},
    "高级警员": {"salary": 12000, "requiredExp": 6000, "level": 4},
    "警长": {"salary": 15000, "requiredExp": 10000, "level": 5},
    "警督": {"salary": 20000, "requiredExp": 15000, "level": 6},
    "总警监": {"salary": 30000, "requiredExp": 25000, "level": 7}
}

# ========== 巡逻事件 ==========

class PatrolEvent(BaseModel):
    """巡逻事件"""
    type: str
    description: str
    exp_reward: int
    money_reward: int
    reputation_change: int = 0

# ========== 升职考核 ==========

class PromotionExam(BaseModel):
    """升职考核结果"""
    user_id: str
    current_rank: str
    target_rank: str
    theory_score: float
    physical_score: float
    practical_score: float
    total_score: float
    passed: bool

# ========== 警察排行榜 ==========

class PoliceRankingEntry(BaseModel):
    """排行榜条目"""
    user_id: str
    name: str
    rank: str
    experience: int
    cases_solved: int
    reputation: int
