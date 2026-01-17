from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


# ========== 消防员技能模型 ==========
class FirefighterSkills(BaseModel):
    """消防员技能"""
    basic_firefighting: int = 0  # 基础灭火
    fire_reconnaissance: int = 0  # 火灾侦察
    search_rescue: int = 0  # 火场搜救
    heat_adaptation: int = 0  # 高温环境适应
    chemical_firefighting: int = 0  # 化学火灾扑救
    high_altitude_rescue: int = 0  # 高空救援
    command_coordination: int = 0  # 指挥协调
    heavy_equipment: int = 0  # 大型设备操作


# ========== 消防员统计 ==========
class FirefighterStats(BaseModel):
    """消防员统计数据"""
    missions_completed: int = 0  # 完成任务数
    missions_failed: int = 0  # 失败任务数
    people_rescued: int = 0  # 救援人数
    casualties: int = 0  # 伤亡人数
    training_completed: int = 0  # 完成训练数
    training_hours: float = 0  # 训练小时数
    medals: int = 0  # 勋章数
    commendations: int = 0  # 嘉奖数


# ========== 消防站信息 ==========
class FireStation(BaseModel):
    """消防站信息"""
    name: str = "新手消防站"
    level: int = 1
    staff: int = 5
    vehicles: List[str] = Field(default_factory=lambda: ["基础消防车"])
    equipment: List[str] = Field(default_factory=lambda: ["基础消防服", "消防水带", "防毒面具"])
    upgrade_progress: int = 0


# ========== 当前任务 ==========
class CurrentMission(BaseModel):
    """当前进行中的任务"""
    fire_id: str
    fire_name: str
    fire_location: str
    difficulty: int
    danger: int
    time_started: str  # ISO时间戳
    time_limit: int  # 秒
    casualties: int  # 被困人数
    status: str = "进行中"  # 进行中/成功/失败
    controlled_fire: bool = False  # 是否控制火势
    support_arrived: bool = False  # 支援是否到达


# ========== 消防员完整信息 ==========
class FirefighterInfo(BaseModel):
    """消防员完整信息"""
    user_id: str
    rank: str = "实习消防员"
    join_date: str = Field(default_factory=lambda: datetime.now().isoformat())
    experience: int = 0
    stamina: int = 100  # 体力
    skills: List[str] = Field(default_factory=list)  # 已学技能名称列表
    equipment: List[str] = Field(default_factory=lambda: ["基础消防服"])
    station: FireStation = Field(default_factory=FireStation)
    stats: FirefighterStats = Field(default_factory=FirefighterStats)
    current_mission: Optional[CurrentMission] = None


# ========== 消防员职级配置 ==========
FIREFIGHTER_RANKS = {
    "实习消防员": {
        "id": "trainee",
        "name": "实习消防员",
        "salary": 200,
        "authority": 10,
        "required_missions": 0,
        "required_training": 0,
        "required_skills": [],
        "equipment_discount": 0,
        "training_discount": 0
    },
    "消防员": {
        "id": "firefighter",
        "name": "消防员",
        "salary": 500,
        "authority": 20,
        "required_missions": 5,
        "required_training": 3,
        "required_skills": ["基础灭火"],
        "equipment_discount": 5,
        "training_discount": 5
    },
    "消防班长": {
        "id": "fire_sergeant",
        "name": "消防班长",
        "salary": 1000,
        "authority": 40,
        "required_missions": 20,
        "required_training": 10,
        "required_skills": ["基础灭火", "火灾侦察", "火场搜救"],
        "equipment_discount": 10,
        "training_discount": 10
    },
    "消防队长": {
        "id": "fire_captain",
        "name": "消防队长",
        "salary": 2000,
        "authority": 60,
        "required_missions": 50,
        "required_training": 25,
        "required_skills": ["火场搜救", "化学火灾扑救", "指挥协调"],
        "equipment_discount": 20,
        "training_discount": 20
    },
    "消防指挥员": {
        "id": "fire_commander",
        "name": "消防指挥员",
        "salary": 3500,
        "authority": 80,
        "required_missions": 100,
        "required_training": 50,
        "required_skills": ["指挥协调", "高空救援", "大型设备操作"],
        "equipment_discount": 30,
        "training_discount": 30
    }
}

# 职级顺序
RANK_ORDER = ["实习消防员", "消防员", "消防班长", "消防队长", "消防指挥员"]


# ========== 火灾类型 ==========
class FireType(BaseModel):
    """火灾类型配置"""
    id: str
    name: str
    description: str
    difficulty: int  # 1-5
    danger: int  # 1-5
    water_required: int
    time_limit: int  # 秒
    xp_reward: int
    money_reward: int
    required_equipment: List[str] = Field(default_factory=list)
    recommended_skills: List[str] = Field(default_factory=list)
    min_rank: str
    casualties_min: int = 0
    casualties_max: int = 5
    possible_causes: List[str] = Field(default_factory=list)


# ========== 消防装备 ==========
class FirefighterEquipment(BaseModel):
    """消防装备"""
    id: str
    name: str
    description: str
    price: int
    protection: int = 0
    durability: int = 100
    mobility: int = 80
    required_rank: str = "消防员"
    attributes: Dict[str, Any] = Field(default_factory=dict)


# ========== 消防技能 ==========
class FirefighterSkill(BaseModel):
    """消防技能配置"""
    id: str
    name: str
    description: str
    learn_cost: int
    time_to_learn: int  # 天
    required_rank: str
    prerequisites: List[str] = Field(default_factory=list)
    buffs: Dict[str, int] = Field(default_factory=dict)  # 各种增益效果


# ========== 救援类型 ==========
class RescueType(BaseModel):
    """救援类型配置"""
    id: str
    name: str
    description: str
    difficulty: int
    danger: int
    time_limit: int
    xp_reward: int
    money_reward: int
    required_equipment: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    min_rank: str
    base_success_rate: int = 70
    skill_bonus: int = 15
    equipment_bonus: int = 10


# ========== 演习结果 ==========
class DrillResult(BaseModel):
    """演习结果"""
    success: bool
    drill_type: str
    exp_gained: int
    stamina_cost: int
    health_lost: int = 0
    new_skill: Optional[str] = None
    success_rate: float


# ========== 灭火行动结果 ==========
class FirefightingResult(BaseModel):
    """灭火行动结果"""
    success: bool
    fire_name: str
    fire_location: str
    method: str
    exp_gained: int = 0
    money_gained: int = 0
    people_rescued: int = 0
    health_lost: int = 0
    stamina_cost: int = 50
    additional_casualties: int = 0
    mission_completed: bool = False
    message: str = ""


# ========== 排行榜条目 ==========
class FirefighterRankingEntry(BaseModel):
    """消防员排行榜条目"""
    user_id: str
    user_name: str
    rank: str
    experience: int
    missions_completed: int
    people_rescued: int
    medals: int


# ========== 旧的兼容模型 ==========
class Mission(BaseModel):
    """任务（兼容旧版）"""
    id: str
    type: str
    difficulty: int
    reward: int
    status: str = "open"  # open/accepted/completed
