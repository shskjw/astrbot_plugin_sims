from pathlib import Path
import uuid
import json
import random
from datetime import datetime
from typing import List, Dict, Optional, Any

from ..common.data_manager import DataManager
from ..common.cooldown import check_cooldown, set_cooldown
from .models import (
    FirefighterInfo, FireStation, CurrentMission, FirefighterStats,
    FireType, FirefighterEquipment, FirefighterSkill, RescueType,
    DrillResult, FirefightingResult, FirefighterRankingEntry,
    FIREFIGHTER_RANKS, RANK_ORDER, Mission
)


class FirefighterLogic:
    def __init__(self, data_manager: DataManager = None):
        self.dm = data_manager or DataManager()
        self.data_path = Path(self.dm.root) / 'data' / 'firefighter'
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # 缓存配置数据
        self._fire_types: Dict[str, dict] = {}
        self._equipment: Dict[str, dict] = {}
        self._skills: Dict[str, dict] = {}
        self._rescue_types: Dict[str, dict] = {}
        
        # 加载配置
        self._load_configs()

    # ========== 配置加载 ==========
    def _load_configs(self):
        """加载所有配置文件"""
        self._fire_types = self._load_json_config('fireTypes.json', self._get_default_fire_types())
        self._equipment = self._load_json_config('equipment.json', self._get_default_equipment())
        self._skills = self._load_json_config('skills.json', self._get_default_skills())
        self._rescue_types = self._load_json_config('rescueTypes.json', self._get_default_rescue_types())

    def _load_json_config(self, filename: str, default: dict) -> dict:
        """加载JSON配置文件"""
        p = self.data_path / filename
        if p.exists():
            try:
                return json.loads(p.read_text(encoding='utf-8'))
            except:
                pass
        # 保存默认配置
        p.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding='utf-8')
        return default

    def _get_default_fire_types(self) -> dict:
        """默认火灾类型配置"""
        return {
            "普通火灾": {
                "id": "fire_normal",
                "name": "普通火灾",
                "description": "一般的建筑或物品起火，难度较低",
                "difficulty": 1,
                "danger": 1,
                "water_required": 500,
                "time_limit": 300,
                "xp_reward": 50,
                "money_reward": 100,
                "required_equipment": ["基础消防服", "消防水带", "防毒面具"],
                "recommended_skills": ["基础灭火", "火灾侦察"],
                "min_rank": "消防员",
                "casualties_min": 0,
                "casualties_max": 2,
                "possible_causes": ["电器短路", "明火引燃", "烟头", "厨房油锅"]
            },
            "工厂火灾": {
                "id": "fire_factory",
                "name": "工厂火灾",
                "description": "工厂起火，可能有化学物质，难度中等",
                "difficulty": 3,
                "danger": 4,
                "water_required": 1500,
                "time_limit": 600,
                "xp_reward": 150,
                "money_reward": 300,
                "required_equipment": ["防化服", "空气呼吸器", "热成像仪", "消防水炮"],
                "recommended_skills": ["化学火灾扑救", "火场搜救", "高温环境适应"],
                "min_rank": "消防班长",
                "casualties_min": 1,
                "casualties_max": 8,
                "possible_causes": ["化学品泄漏", "机械摩擦", "电气故障", "易燃品储存不当"]
            },
            "高层建筑火灾": {
                "id": "fire_highrise",
                "name": "高层建筑火灾",
                "description": "高层建筑起火，疏散困难，环境复杂",
                "difficulty": 4,
                "danger": 4,
                "water_required": 2000,
                "time_limit": 900,
                "xp_reward": 200,
                "money_reward": 400,
                "required_equipment": ["高层灭火装备", "登高器械", "便携式水泵", "消防绳索"],
                "recommended_skills": ["高空救援", "火场搜救"],
                "min_rank": "消防班长",
                "casualties_min": 2,
                "casualties_max": 15,
                "possible_causes": ["电气线路老化", "易燃装修材料", "明火引燃", "纵火"]
            },
            "森林火灾": {
                "id": "fire_forest",
                "name": "森林火灾",
                "description": "森林地区大面积起火，影响范围广",
                "difficulty": 5,
                "danger": 5,
                "water_required": 5000,
                "time_limit": 1800,
                "xp_reward": 300,
                "money_reward": 600,
                "required_equipment": ["森林消防装备", "风力灭火机", "大型水炮"],
                "recommended_skills": ["指挥协调", "大型设备操作"],
                "min_rank": "消防队长",
                "casualties_min": 0,
                "casualties_max": 5,
                "possible_causes": ["雷击", "烧荒失火", "野炊", "香烟烟头"]
            },
            "危险品仓库火灾": {
                "id": "fire_hazardous",
                "name": "危险品仓库火灾",
                "description": "存放危险化学品仓库起火，爆炸风险高",
                "difficulty": 5,
                "danger": 5,
                "water_required": 3000,
                "time_limit": 1200,
                "xp_reward": 350,
                "money_reward": 700,
                "required_equipment": ["全套防化服", "高级空气呼吸器", "化学泡沫灭火器"],
                "recommended_skills": ["化学火灾扑救", "指挥协调", "火灾侦察"],
                "min_rank": "消防队长",
                "casualties_min": 2,
                "casualties_max": 20,
                "possible_causes": ["化学反应", "存储不当", "温度过高", "易燃品混放"]
            }
        }

    def _get_default_equipment(self) -> dict:
        """默认装备配置"""
        return {
            "基础消防服": {
                "id": "basic_suit",
                "name": "基础消防服",
                "description": "基础防护装备，可以抵抗一般热度和短时间明火",
                "price": 500,
                "protection": 20,
                "durability": 100,
                "mobility": 80,
                "required_rank": "消防员"
            },
            "防毒面具": {
                "id": "gas_mask",
                "name": "防毒面具",
                "description": "过滤有毒气体，保障呼吸安全的装备",
                "price": 300,
                "protection": 15,
                "durability": 80,
                "mobility": 90,
                "required_rank": "消防员"
            },
            "消防水带": {
                "id": "fire_hose",
                "name": "消防水带",
                "description": "输送灭火用水的关键装备",
                "price": 200,
                "protection": 0,
                "durability": 120,
                "mobility": 70,
                "required_rank": "消防员"
            },
            "空气呼吸器": {
                "id": "breathing_apparatus",
                "name": "空气呼吸器",
                "description": "在烟雾环境中提供清洁空气的设备",
                "price": 800,
                "protection": 40,
                "durability": 90,
                "mobility": 70,
                "required_rank": "消防班长"
            },
            "热成像仪": {
                "id": "thermal_imager",
                "name": "热成像仪",
                "description": "在烟雾中识别热源，帮助搜救和火点定位",
                "price": 1200,
                "protection": 0,
                "durability": 100,
                "mobility": 95,
                "required_rank": "消防班长"
            },
            "消防水炮": {
                "id": "water_cannon",
                "name": "消防水炮",
                "description": "大流量灭火设备，适合大规模火灾",
                "price": 2000,
                "protection": 0,
                "durability": 150,
                "mobility": 30,
                "required_rank": "消防队长"
            },
            "高级防化服": {
                "id": "hazmat_suit",
                "name": "高级防化服",
                "description": "抵抗化学物质和高温的特种装备",
                "price": 3000,
                "protection": 80,
                "durability": 100,
                "mobility": 50,
                "required_rank": "消防队长"
            },
            "消防无人机": {
                "id": "fire_drone",
                "name": "消防无人机",
                "description": "用于侦察和监测火场的高科技设备",
                "price": 5000,
                "protection": 0,
                "durability": 80,
                "mobility": 100,
                "required_rank": "消防指挥员"
            }
        }

    def _get_default_skills(self) -> dict:
        """默认技能配置"""
        return {
            "基础灭火": {
                "id": "basic_firefighting",
                "name": "基础灭火",
                "description": "掌握基本的灭火技巧和方法",
                "learn_cost": 100,
                "time_to_learn": 1,
                "required_rank": "消防员",
                "prerequisites": [],
                "buffs": {"effectiveness": 10}
            },
            "火灾侦察": {
                "id": "fire_reconnaissance",
                "name": "火灾侦察",
                "description": "评估火场情况和结构安全的能力",
                "learn_cost": 150,
                "time_to_learn": 2,
                "required_rank": "消防员",
                "prerequisites": ["基础灭火"],
                "buffs": {"safety": 15}
            },
            "火场搜救": {
                "id": "search_and_rescue",
                "name": "火场搜救",
                "description": "在火场中有效搜寻和救助受困人员的技能",
                "learn_cost": 300,
                "time_to_learn": 3,
                "required_rank": "消防班长",
                "prerequisites": ["火灾侦察"],
                "buffs": {"rescue_efficiency": 20, "survivor_save": 25}
            },
            "高温环境适应": {
                "id": "heat_adaptation",
                "name": "高温环境适应",
                "description": "提高在高温环境中工作的能力和耐受力",
                "learn_cost": 400,
                "time_to_learn": 5,
                "required_rank": "消防班长",
                "prerequisites": ["基础灭火"],
                "buffs": {"heat_resistance": 30, "stamina_in_heat": 25}
            },
            "化学火灾扑救": {
                "id": "chemical_firefighting",
                "name": "化学火灾扑救",
                "description": "应对化学物质引起的特殊火灾的专业技能",
                "learn_cost": 500,
                "time_to_learn": 7,
                "required_rank": "消防队长",
                "prerequisites": ["基础灭火", "火灾侦察"],
                "buffs": {"chemical_fire": 35, "toxin_resistance": 20}
            },
            "高空救援": {
                "id": "high_altitude_rescue",
                "name": "高空救援",
                "description": "在高层建筑和高空环境进行救援的技能",
                "learn_cost": 600,
                "time_to_learn": 10,
                "required_rank": "消防队长",
                "prerequisites": ["火场搜救"],
                "buffs": {"height_fear_reduction": 40, "rope_techniques": 30}
            },
            "指挥协调": {
                "id": "command_coordination",
                "name": "指挥协调",
                "description": "在火场指挥和协调多个救援小组的能力",
                "learn_cost": 800,
                "time_to_learn": 14,
                "required_rank": "消防指挥员",
                "prerequisites": ["火灾侦察", "火场搜救"],
                "buffs": {"team_efficiency": 25, "communication": 30}
            },
            "大型设备操作": {
                "id": "heavy_equipment_operation",
                "name": "大型设备操作",
                "description": "操作大型消防设备和车辆的专业技能",
                "learn_cost": 700,
                "time_to_learn": 12,
                "required_rank": "消防队长",
                "prerequisites": ["基础灭火"],
                "buffs": {"equipment_efficiency": 25, "mechanical_knowledge": 30}
            }
        }

    def _get_default_rescue_types(self) -> dict:
        """默认救援类型配置"""
        return {
            "被困人员救援": {
                "id": "trapped_rescue",
                "name": "被困人员救援",
                "description": "搜救被火灾或其他灾害困住的人员",
                "difficulty": 3,
                "danger": 4,
                "time_limit": 300,
                "xp_reward": 100,
                "money_reward": 200,
                "required_equipment": ["防毒面具", "空气呼吸器", "热成像仪"],
                "required_skills": ["火场搜救", "高温环境适应"],
                "min_rank": "消防员",
                "base_success_rate": 70,
                "skill_bonus": 15,
                "equipment_bonus": 10
            },
            "电梯故障救援": {
                "id": "elevator_rescue",
                "name": "电梯故障救援",
                "description": "营救被困在故障电梯中的人员",
                "difficulty": 2,
                "danger": 2,
                "time_limit": 180,
                "xp_reward": 60,
                "money_reward": 120,
                "required_equipment": ["基础消防服"],
                "required_skills": ["火灾侦察"],
                "min_rank": "消防员",
                "base_success_rate": 85,
                "skill_bonus": 10,
                "equipment_bonus": 5
            },
            "交通事故救援": {
                "id": "traffic_accident_rescue",
                "name": "交通事故救援",
                "description": "解救交通事故中被困的受害者",
                "difficulty": 3,
                "danger": 3,
                "time_limit": 240,
                "xp_reward": 80,
                "money_reward": 150,
                "required_equipment": ["基础消防服", "消防水带"],
                "required_skills": ["火场搜救", "指挥协调"],
                "min_rank": "消防班长",
                "base_success_rate": 75,
                "skill_bonus": 15,
                "equipment_bonus": 10
            },
            "水域救援": {
                "id": "water_rescue",
                "name": "水域救援",
                "description": "救援溺水人员或水中被困者",
                "difficulty": 4,
                "danger": 4,
                "time_limit": 180,
                "xp_reward": 120,
                "money_reward": 250,
                "required_equipment": ["基础消防服"],
                "required_skills": ["火场搜救"],
                "min_rank": "消防班长",
                "base_success_rate": 65,
                "skill_bonus": 20,
                "equipment_bonus": 15
            }
        }

    # ========== 用户数据管理 ==========
    def _firefighters_file(self) -> Path:
        return self.data_path / 'firefighters.json'

    def _load_firefighters(self) -> dict:
        p = self._firefighters_file()
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding='utf-8'))

    def _save_firefighters(self, data: dict):
        p = self._firefighters_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _get_user_firefighter(self, user_id: str) -> Optional[FirefighterInfo]:
        """获取用户消防员信息"""
        firefighters = self._load_firefighters()
        if user_id in firefighters:
            return FirefighterInfo(**firefighters[user_id])
        return None

    def _save_user_firefighter(self, user_id: str, info: FirefighterInfo):
        """保存用户消防员信息"""
        firefighters = self._load_firefighters()
        firefighters[user_id] = info.dict()
        self._save_firefighters(firefighters)

    # ========== 辅助方法 ==========
    def _get_rank_index(self, rank: str) -> int:
        """获取职级索引"""
        try:
            return RANK_ORDER.index(rank)
        except ValueError:
            return 0

    def _can_access_rank(self, user_rank: str, required_rank: str) -> bool:
        """检查用户职级是否满足要求"""
        return self._get_rank_index(user_rank) >= self._get_rank_index(required_rank)

    def _check_rank_up(self, info: FirefighterInfo) -> Optional[str]:
        """检查是否可以晋升"""
        current_index = self._get_rank_index(info.rank)
        if current_index >= len(RANK_ORDER) - 1:
            return None
        
        next_rank = RANK_ORDER[current_index + 1]
        next_config = FIREFIGHTER_RANKS.get(next_rank)
        if not next_config:
            return None
        
        # 检查任务数
        if info.stats.missions_completed < next_config['required_missions']:
            return None
        # 检查训练数
        if info.stats.training_completed < next_config['required_training']:
            return None
        # 检查技能
        for skill in next_config['required_skills']:
            if skill not in info.skills:
                return None
        
        return next_rank

    # ========== 核心功能 ==========
    def join_fire_department(self, user_id: str) -> FirefighterInfo:
        """加入消防队"""
        rem = check_cooldown(user_id, 'firefighter', 'join')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        # 检查是否已经是消防员
        existing = self._get_user_firefighter(user_id)
        if existing:
            raise ValueError("你已经是消防队的一员了！")
        
        # 检查用户基础数据
        user = self.dm.load_user(user_id) or {}
        stamina = user.get('stamina', 100)
        life = user.get('life', 100)
        
        if stamina < 60:
            raise ValueError("体力不足，无法加入消防队！消防工作需要良好的体力支持。")
        if life < 70:
            raise ValueError("生命值太低，无法加入消防队！请先恢复健康。")
        
        # 创建消防员信息
        info = FirefighterInfo(user_id=user_id)
        self._save_user_firefighter(user_id, info)
        
        set_cooldown(user_id, 'firefighter', 'join', 60)
        return info

    def get_firefighter_info(self, user_id: str) -> FirefighterInfo:
        """获取消防员信息"""
        rem = check_cooldown(user_id, 'firefighter', 'info')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        info = self._get_user_firefighter(user_id)
        if not info:
            raise ValueError("你还不是消防队的一员！请先使用 加入消防队 指令。")
        
        set_cooldown(user_id, 'firefighter', 'info', 3)
        return info

    def get_station_info(self, user_id: str) -> dict:
        """获取消防站信息"""
        info = self._get_user_firefighter(user_id)
        if not info:
            raise ValueError("你还不是消防队的一员！")
        
        station = info.station
        level = station.level
        return {
            "name": station.name,
            "level": level,
            "staff": station.staff,
            "max_staff": 5 + (level - 1) * 3,
            "vehicles": station.vehicles,
            "max_vehicles": 1 + (level - 1),
            "equipment": station.equipment,
            "upgrade_progress": station.upgrade_progress,
            "response_time": max(5 - (level - 1) * 0.5, 1)
        }

    def firefighting_drill(self, user_id: str) -> DrillResult:
        """消防演习"""
        rem = check_cooldown(user_id, 'firefighter', 'drill')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        info = self._get_user_firefighter(user_id)
        if not info:
            raise ValueError("你还不是消防队的一员！")
        
        # 检查体力
        user = self.dm.load_user(user_id) or {}
        stamina = user.get('stamina', 100)
        if stamina < 30:
            raise ValueError("体力不足，无法进行消防演习！请先休息恢复体力。")
        
        # 随机选择演习类型
        drill_types = ["灭火基础训练", "紧急疏散演练", "搜救技术培训", "呼吸器使用训练", "高空救援演练"]
        drill_type = random.choice(drill_types)
        
        # 计算成功率
        base_rate = 70
        buff = 0
        
        # 职级加成
        rank_buffs = {"消防员": 5, "消防班长": 10, "消防队长": 15, "消防指挥员": 20}
        buff += rank_buffs.get(info.rank, 0)
        
        # 装备加成
        if "基础消防服" in info.equipment:
            buff += 5
        if "防毒面具" in info.equipment:
            buff += 5
        if "消防水带" in info.equipment:
            buff += 3
        
        # 技能加成
        if "基础灭火" in info.skills:
            buff += 8
        if "火灾侦察" in info.skills:
            buff += 10
        
        final_rate = min(base_rate + buff, 95)
        success = random.random() * 100 < final_rate
        
        # 更新数据
        user['stamina'] = stamina - 30
        info.stats.training_completed += 1
        info.stats.training_hours += 2
        
        health_lost = 0
        new_skill = None
        
        if success:
            exp_gain = 20 + random.randint(0, 10)
            info.experience += exp_gain
            
            # 小概率学会基础灭火
            if "基础灭火" not in info.skills and random.random() < 0.3:
                info.skills.append("基础灭火")
                new_skill = "基础灭火"
        else:
            exp_gain = 5 + random.randint(0, 5)
            info.experience += exp_gain
            health_lost = random.randint(1, 5)
            user['life'] = user.get('life', 100) - health_lost
        
        # 检查晋升
        new_rank = self._check_rank_up(info)
        if new_rank:
            info.rank = new_rank
        
        self.dm.save_user(user_id, user)
        self._save_user_firefighter(user_id, info)
        
        set_cooldown(user_id, 'firefighter', 'drill', 60)
        
        return DrillResult(
            success=success,
            drill_type=drill_type,
            exp_gained=exp_gain,
            stamina_cost=30,
            health_lost=health_lost,
            new_skill=new_skill,
            success_rate=final_rate
        )

    def start_firefighting_mission(self, user_id: str) -> dict:
        """开始灭火行动"""
        rem = check_cooldown(user_id, 'firefighter', 'mission')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        info = self._get_user_firefighter(user_id)
        if not info:
            raise ValueError("你还不是消防队的一员！")
        
        # 检查体力和生命值
        user = self.dm.load_user(user_id) or {}
        if user.get('stamina', 100) < 50:
            raise ValueError("体力不足，无法执行灭火任务！")
        if user.get('life', 100) < 60:
            raise ValueError("健康状况不佳，无法执行灭火任务！")
        
        # 检查是否有进行中的任务
        if info.current_mission and info.current_mission.status == "进行中":
            raise ValueError("你已有进行中的灭火任务！请先完成当前任务。")
        
        # 筛选可接取的火灾类型
        available_fires = [
            (name, config) for name, config in self._fire_types.items()
            if self._can_access_rank(info.rank, config.get('min_rank', '消防员'))
        ]
        
        if not available_fires:
            raise ValueError("当前没有适合你职称等级的火灾任务。")
        
        # 随机选择火灾
        fire_name, fire_config = random.choice(available_fires)
        
        # 随机地点
        locations = ["居民区", "商业街", "工业园区", "学校", "医院", "商场", "办公楼", "农田", "森林公园", "加油站"]
        location = random.choice(locations)
        
        # 随机伤亡人数
        casualties = random.randint(
            fire_config.get('casualties_min', 0),
            fire_config.get('casualties_max', 5)
        )
        
        # 创建任务
        mission = CurrentMission(
            fire_id=fire_config['id'],
            fire_name=fire_name,
            fire_location=location,
            difficulty=fire_config['difficulty'],
            danger=fire_config['danger'],
            time_started=datetime.now().isoformat(),
            time_limit=fire_config['time_limit'],
            casualties=casualties
        )
        
        info.current_mission = mission
        self._save_user_firefighter(user_id, info)
        
        set_cooldown(user_id, 'firefighter', 'mission', 30)
        
        return {
            "fire_name": fire_name,
            "fire_location": location,
            "difficulty": fire_config['difficulty'],
            "danger": fire_config['danger'],
            "casualties": casualties,
            "time_limit": fire_config['time_limit'],
            "required_equipment": fire_config.get('required_equipment', []),
            "recommended_skills": fire_config.get('recommended_skills', []),
            "methods": ["直接灭火", "疏散人员", "控制火势", "救援伤员", "请求支援"]
        }

    def fire_control(self, user_id: str, method: str) -> FirefightingResult:
        """火灾控制"""
        rem = check_cooldown(user_id, 'firefighter', 'control')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        info = self._get_user_firefighter(user_id)
        if not info:
            raise ValueError("你还不是消防队的一员！")
        
        if not info.current_mission or info.current_mission.status != "进行中":
            raise ValueError("你当前没有进行中的灭火任务！")
        
        valid_methods = ["直接灭火", "疏散人员", "控制火势", "救援伤员", "请求支援"]
        if method not in valid_methods:
            raise ValueError(f"无效的灭火方案！请选择：{', '.join(valid_methods)}")
        
        mission = info.current_mission
        fire_config = self._fire_types.get(mission.fire_name, {})
        
        # 检查是否超时
        start_time = datetime.fromisoformat(mission.time_started)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if elapsed > mission.time_limit:
            mission.status = "失败"
            info.stats.missions_failed += 1
            info.current_mission = None
            
            user = self.dm.load_user(user_id) or {}
            user['life'] = user.get('life', 100) - 10
            user['stamina'] = user.get('stamina', 100) - 50
            self.dm.save_user(user_id, user)
            self._save_user_firefighter(user_id, info)
            
            set_cooldown(user_id, 'firefighter', 'control', 10)
            
            return FirefightingResult(
                success=False,
                fire_name=mission.fire_name,
                fire_location=mission.fire_location,
                method=method,
                health_lost=10,
                stamina_cost=50,
                message="任务已超时！火势已经失控，灭火行动失败。"
            )
        
        # 计算成功率
        base_rate = 60
        buff = 0
        
        # 方法加成
        if method == "直接灭火":
            if mission.fire_name == "普通火灾":
                buff += 20
            if mission.fire_name == "危险品仓库火灾":
                buff -= 30
        elif method == "疏散人员":
            if mission.fire_name == "高层建筑火灾":
                buff += 25
            if mission.casualties > 5:
                buff += 15
        elif method == "控制火势":
            if mission.fire_name == "森林火灾":
                buff += 20
            if mission.fire_name == "工厂火灾":
                buff += 15
        elif method == "救援伤员":
            if mission.casualties > 0:
                buff += mission.casualties * 5
        elif method == "请求支援":
            buff += 10
        
        # 装备加成
        required_equipment = fire_config.get('required_equipment', [])
        for equip in required_equipment:
            if equip in info.equipment:
                buff += 5
            else:
                buff -= 10
        
        # 技能加成
        recommended_skills = fire_config.get('recommended_skills', [])
        for skill in recommended_skills:
            if skill in info.skills:
                buff += 10
        
        # 职级加成
        rank_buffs = {"消防员": 5, "消防班长": 10, "消防队长": 15, "消防指挥员": 20}
        buff += rank_buffs.get(info.rank, 0)
        
        # 之前的控制和支援加成
        if mission.controlled_fire:
            buff += 25
        if mission.support_arrived:
            buff += 40
        
        final_rate = max(10, min(base_rate + buff, 95))
        success = random.random() * 100 < final_rate
        
        user = self.dm.load_user(user_id) or {}
        user['stamina'] = user.get('stamina', 100) - 50
        
        result = FirefightingResult(
            success=success,
            fire_name=mission.fire_name,
            fire_location=mission.fire_location,
            method=method,
            stamina_cost=50
        )
        
        if success:
            if method == "直接灭火":
                # 完全灭火，任务完成
                mission.status = "成功"
                info.stats.missions_completed += 1
                info.stats.people_rescued += mission.casualties
                
                exp_gain = fire_config.get('xp_reward', 50)
                money_gain = fire_config.get('money_reward', 100)
                info.experience += exp_gain
                user['money'] = user.get('money', 0) + money_gain
                
                # 可能受伤
                health_lost = 0
                if random.random() < 0.3:
                    health_lost = random.randint(5, 10)
                    user['life'] = user.get('life', 100) - health_lost
                
                result.exp_gained = exp_gain
                result.money_gained = money_gain
                result.people_rescued = mission.casualties
                result.health_lost = health_lost
                result.mission_completed = True
                result.message = f"灭火行动成功！成功救出所有 {mission.casualties} 名被困人员！"
                
                info.current_mission = None
                
            elif method == "疏散人员":
                if mission.casualties > 0:
                    saved = int(mission.casualties * 0.8) or 1
                    info.stats.people_rescued += saved
                    mission.casualties -= saved
                    result.people_rescued = saved
                    result.message = f"成功疏散了 {saved} 名被困人员！剩余被困人数：{mission.casualties}"
                else:
                    result.message = "现场无被困人员需要疏散。"
                    
            elif method == "控制火势":
                mission.controlled_fire = True
                result.message = "成功控制了火势蔓延！后续灭火行动的成功率将提高25%！"
                
            elif method == "救援伤员":
                if mission.casualties > 0:
                    saved = mission.casualties
                    info.stats.people_rescued += saved
                    bonus_exp = saved * 10
                    bonus_money = saved * 20
                    info.experience += bonus_exp
                    user['money'] = user.get('money', 0) + bonus_money
                    mission.casualties = 0
                    
                    result.people_rescued = saved
                    result.exp_gained = bonus_exp
                    result.money_gained = bonus_money
                    result.message = f"英勇救援！成功救出了所有 {saved} 名被困人员！"
                else:
                    result.message = "现场无被困人员需要救援。"
                    
            elif method == "请求支援":
                mission.support_arrived = True
                result.message = "支援已到达现场！后续所有行动的成功率将提高40%！"
            
            # 检查任务是否全部完成
            if method != "直接灭火" and mission.casualties == 0 and (mission.controlled_fire or mission.support_arrived):
                mission.status = "成功"
                info.stats.missions_completed += 1
                
                exp_gain = fire_config.get('xp_reward', 50)
                money_gain = fire_config.get('money_reward', 100)
                info.experience += exp_gain
                user['money'] = user.get('money', 0) + money_gain
                
                result.exp_gained += exp_gain
                result.money_gained += money_gain
                result.mission_completed = True
                result.message += f"\n灭火行动圆满成功！获得经验：{exp_gain}，奖金：{money_gain}元"
                
                info.current_mission = None
        else:
            # 行动失败
            health_lost = random.randint(5, 15)
            user['life'] = user.get('life', 100) - health_lost
            result.health_lost = health_lost
            
            # 检查是否严重失败
            if user.get('life', 100) < 30 or final_rate < 20:
                mission.status = "失败"
                info.stats.missions_failed += 1
                
                additional_casualties = random.randint(1, 3)
                info.stats.casualties += additional_casualties
                result.additional_casualties = additional_casualties
                result.message = f"灭火行动失败！情况恶化，你们被迫撤退。伤亡增加：{additional_casualties}人"
                
                info.current_mission = None
            else:
                result.message = f"控制失败！{method}未能有效执行。请尝试其他方法。"
        
        # 检查晋升
        new_rank = self._check_rank_up(info)
        if new_rank:
            info.rank = new_rank
        
        self.dm.save_user(user_id, user)
        self._save_user_firefighter(user_id, info)
        
        set_cooldown(user_id, 'firefighter', 'control', 15)
        
        return result

    def learn_skill(self, user_id: str, skill_name: str) -> dict:
        """学习消防技能"""
        rem = check_cooldown(user_id, 'firefighter', 'learn')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        info = self._get_user_firefighter(user_id)
        if not info:
            raise ValueError("你还不是消防队的一员！")
        
        if skill_name not in self._skills:
            available = '、'.join(self._skills.keys())
            raise ValueError(f"未找到该技能！可学习的技能有：{available}")
        
        skill = self._skills[skill_name]
        
        if skill_name in info.skills:
            raise ValueError(f"你已经掌握了【{skill_name}】技能！")
        
        if not self._can_access_rank(info.rank, skill.get('required_rank', '消防员')):
            raise ValueError(f"职称不足！需要{skill['required_rank']}或以上职称。")
        
        # 检查前置技能
        for prereq in skill.get('prerequisites', []):
            if prereq not in info.skills:
                raise ValueError(f"学习【{skill_name}】需要先掌握【{prereq}】技能！")
        
        # 检查金钱
        user = self.dm.load_user(user_id) or {}
        cost = skill.get('learn_cost', 100)
        if user.get('money', 0) < cost:
            raise ValueError(f"金钱不足！需要{cost}元。")
        
        # 扣费并学习
        user['money'] -= cost
        info.skills.append(skill_name)
        info.experience += 30
        
        self.dm.save_user(user_id, user)
        self._save_user_firefighter(user_id, info)
        
        set_cooldown(user_id, 'firefighter', 'learn', 30)
        
        return {
            "skill_name": skill_name,
            "description": skill['description'],
            "cost": cost,
            "buffs": skill.get('buffs', {})
        }

    def get_equipment_shop(self) -> List[dict]:
        """获取装备商店"""
        return [
            {
                "name": name,
                "description": config['description'],
                "price": config['price'],
                "protection": config.get('protection', 0),
                "required_rank": config.get('required_rank', '消防员')
            }
            for name, config in self._equipment.items()
        ]

    def buy_equipment(self, user_id: str, equipment_name: str) -> dict:
        """购买装备"""
        rem = check_cooldown(user_id, 'firefighter', 'buy')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        info = self._get_user_firefighter(user_id)
        if not info:
            raise ValueError("你还不是消防队的一员！")
        
        if equipment_name not in self._equipment:
            raise ValueError(f"未找到该装备！")
        
        equipment = self._equipment[equipment_name]
        
        if equipment_name in info.equipment:
            raise ValueError(f"你已经拥有【{equipment_name}】！")
        
        if not self._can_access_rank(info.rank, equipment.get('required_rank', '消防员')):
            raise ValueError(f"职称不足！需要{equipment['required_rank']}或以上职称。")
        
        # 检查金钱（含折扣）
        user = self.dm.load_user(user_id) or {}
        rank_config = FIREFIGHTER_RANKS.get(info.rank, {})
        discount = rank_config.get('equipment_discount', 0)
        price = int(equipment['price'] * (100 - discount) / 100)
        
        if user.get('money', 0) < price:
            raise ValueError(f"金钱不足！需要{price}元（已享{discount}%折扣）。")
        
        user['money'] -= price
        info.equipment.append(equipment_name)
        
        self.dm.save_user(user_id, user)
        self._save_user_firefighter(user_id, info)
        
        set_cooldown(user_id, 'firefighter', 'buy', 10)
        
        return {
            "equipment_name": equipment_name,
            "description": equipment['description'],
            "price": price,
            "discount": discount
        }

    def rescue_operation(self, user_id: str, rescue_type: str) -> dict:
        """救援行动"""
        rem = check_cooldown(user_id, 'firefighter', 'rescue')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        info = self._get_user_firefighter(user_id)
        if not info:
            raise ValueError("你还不是消防队的一员！")
        
        if rescue_type not in self._rescue_types:
            available = '、'.join(self._rescue_types.keys())
            raise ValueError(f"未找到该救援类型！可选：{available}")
        
        rescue = self._rescue_types[rescue_type]
        
        if not self._can_access_rank(info.rank, rescue.get('min_rank', '消防员')):
            raise ValueError(f"职称不足！需要{rescue['min_rank']}或以上职称。")
        
        # 检查体力
        user = self.dm.load_user(user_id) or {}
        if user.get('stamina', 100) < 40:
            raise ValueError("体力不足，无法执行救援任务！")
        
        # 计算成功率
        base_rate = rescue.get('base_success_rate', 70)
        buff = 0
        
        # 装备加成
        for equip in rescue.get('required_equipment', []):
            if equip in info.equipment:
                buff += rescue.get('equipment_bonus', 10) // len(rescue.get('required_equipment', [1]))
        
        # 技能加成
        for skill in rescue.get('required_skills', []):
            if skill in info.skills:
                buff += rescue.get('skill_bonus', 15) // len(rescue.get('required_skills', [1]))
        
        final_rate = min(base_rate + buff, 95)
        success = random.random() * 100 < final_rate
        
        user['stamina'] = user.get('stamina', 100) - 40
        
        if success:
            exp_gain = rescue.get('xp_reward', 100)
            money_gain = rescue.get('money_reward', 200)
            people_saved = random.randint(1, 3)
            
            info.experience += exp_gain
            info.stats.people_rescued += people_saved
            user['money'] = user.get('money', 0) + money_gain
            
            result = {
                "success": True,
                "rescue_type": rescue_type,
                "exp_gained": exp_gain,
                "money_gained": money_gain,
                "people_saved": people_saved,
                "health_lost": 0,
                "message": f"救援成功！成功救出 {people_saved} 人！"
            }
        else:
            health_lost = random.randint(5, 15)
            user['life'] = user.get('life', 100) - health_lost
            exp_gain = rescue.get('xp_reward', 100) // 4
            info.experience += exp_gain
            
            result = {
                "success": False,
                "rescue_type": rescue_type,
                "exp_gained": exp_gain,
                "money_gained": 0,
                "people_saved": 0,
                "health_lost": health_lost,
                "message": "救援失败，但你从中学到了经验。"
            }
        
        # 检查晋升
        new_rank = self._check_rank_up(info)
        if new_rank:
            info.rank = new_rank
        
        self.dm.save_user(user_id, user)
        self._save_user_firefighter(user_id, info)
        
        set_cooldown(user_id, 'firefighter', 'rescue', 120)
        
        return result

    def apply_for_promotion(self, user_id: str) -> dict:
        """申请职称晋升"""
        rem = check_cooldown(user_id, 'firefighter', 'promotion')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        info = self._get_user_firefighter(user_id)
        if not info:
            raise ValueError("你还不是消防队的一员！")
        
        current_index = self._get_rank_index(info.rank)
        if current_index >= len(RANK_ORDER) - 1:
            raise ValueError("你已经是最高职称了！")
        
        next_rank = RANK_ORDER[current_index + 1]
        next_config = FIREFIGHTER_RANKS[next_rank]
        
        # 检查条件
        missing = []
        if info.stats.missions_completed < next_config['required_missions']:
            missing.append(f"任务数: {info.stats.missions_completed}/{next_config['required_missions']}")
        if info.stats.training_completed < next_config['required_training']:
            missing.append(f"训练数: {info.stats.training_completed}/{next_config['required_training']}")
        
        missing_skills = [s for s in next_config['required_skills'] if s not in info.skills]
        if missing_skills:
            missing.append(f"缺少技能: {', '.join(missing_skills)}")
        
        if missing:
            return {
                "success": False,
                "current_rank": info.rank,
                "next_rank": next_rank,
                "missing": missing,
                "message": f"晋升条件不足！\n" + "\n".join(missing)
            }
        
        # 晋升成功
        info.rank = next_rank
        info.experience += 100
        
        self._save_user_firefighter(user_id, info)
        
        set_cooldown(user_id, 'firefighter', 'promotion', 300)
        
        return {
            "success": True,
            "old_rank": RANK_ORDER[current_index],
            "new_rank": next_rank,
            "salary": next_config['salary'],
            "message": f"恭喜晋升为【{next_rank}】！工资提升至 {next_config['salary']} 元/天"
        }

    def upgrade_station(self, user_id: str) -> dict:
        """升级消防站"""
        rem = check_cooldown(user_id, 'firefighter', 'upgrade')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        info = self._get_user_firefighter(user_id)
        if not info:
            raise ValueError("你还不是消防队的一员！")
        
        if info.rank not in ["消防队长", "消防指挥员"]:
            raise ValueError("只有消防队长以上职称才能升级消防站！")
        
        station = info.station
        if station.level >= 5:
            raise ValueError("消防站已达最高等级！")
        
        # 计算升级费用
        upgrade_cost = station.level * 2000
        
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < upgrade_cost:
            raise ValueError(f"金钱不足！升级需要 {upgrade_cost} 元。")
        
        user['money'] -= upgrade_cost
        station.level += 1
        station.staff += 3
        station.upgrade_progress = 0
        
        # 添加新车辆
        new_vehicles = ["消防云梯车", "化学消防车", "抢险救援车", "泡沫消防车"]
        if station.level - 2 < len(new_vehicles):
            station.vehicles.append(new_vehicles[station.level - 2])
        
        self.dm.save_user(user_id, user)
        self._save_user_firefighter(user_id, info)
        
        set_cooldown(user_id, 'firefighter', 'upgrade', 600)
        
        return {
            "new_level": station.level,
            "cost": upgrade_cost,
            "staff": station.staff,
            "vehicles": station.vehicles,
            "message": f"消防站升级成功！当前等级：{station.level}"
        }

    def get_firefighter_ranking(self, sort_by: str = "experience") -> List[FirefighterRankingEntry]:
        """获取消防员排行榜"""
        firefighters = self._load_firefighters()
        
        entries = []
        for uid, data in firefighters.items():
            user = self.dm.load_user(uid) or {}
            entries.append(FirefighterRankingEntry(
                user_id=uid,
                user_name=user.get('name', f'用户{uid[:6]}'),
                rank=data.get('rank', '实习消防员'),
                experience=data.get('experience', 0),
                missions_completed=data.get('stats', {}).get('missions_completed', 0),
                people_rescued=data.get('stats', {}).get('people_rescued', 0),
                medals=data.get('stats', {}).get('medals', 0)
            ))
        
        # 排序
        if sort_by == "missions":
            entries.sort(key=lambda x: x.missions_completed, reverse=True)
        elif sort_by == "rescued":
            entries.sort(key=lambda x: x.people_rescued, reverse=True)
        elif sort_by == "medals":
            entries.sort(key=lambda x: x.medals, reverse=True)
        else:
            entries.sort(key=lambda x: x.experience, reverse=True)
        
        return entries[:20]

    def get_skills_list(self) -> List[dict]:
        """获取技能列表"""
        return [
            {
                "name": name,
                "description": config['description'],
                "cost": config['learn_cost'],
                "required_rank": config.get('required_rank', '消防员'),
                "prerequisites": config.get('prerequisites', [])
            }
            for name, config in self._skills.items()
        ]

    def get_rescue_types(self) -> List[dict]:
        """获取救援类型列表"""
        return [
            {
                "name": name,
                "description": config['description'],
                "difficulty": config['difficulty'],
                "xp_reward": config['xp_reward'],
                "money_reward": config['money_reward'],
                "min_rank": config.get('min_rank', '消防员')
            }
            for name, config in self._rescue_types.items()
        ]

    # ========== 兼容旧版任务系统 ==========
    def _missions_file(self):
        return self.data_path / 'missions.json'

    def _load_missions(self):
        p = self._missions_file()
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding='utf-8'))

    def _save_missions(self, data):
        p = self._missions_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def create_mission(self, mtype: str, difficulty: int = 1, reward: int = 10):
        missions = self._load_missions()
        mid = str(uuid.uuid4())[:8]
        m = Mission(id=mid, type=mtype, difficulty=difficulty, reward=reward).dict()
        missions[mid] = m
        self._save_missions(missions)
        return m

    def list_missions(self):
        return list(self._load_missions().values())

    def accept_mission(self, user_id: str, mission_id: str):
        rem = check_cooldown(user_id, 'firefighter', 'accept')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        missions = self._load_missions()
        m = missions.get(mission_id)
        if not m:
            raise ValueError('任务不存在')
        if m.get('status') != 'open':
            raise ValueError('任务不可接取')
        m['status'] = 'accepted'
        m['accepted_by'] = user_id
        missions[mission_id] = m
        self._save_missions(missions)
        set_cooldown(user_id, 'firefighter', 'accept', 5)
        return m

    def complete_mission(self, user_id: str, mission_id: str):
        missions = self._load_missions()
        m = missions.get(mission_id)
        if not m:
            raise ValueError('任务不存在')
        if m.get('accepted_by') != user_id:
            raise ValueError('你未接取该任务')
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) + m.get('reward', 0)
        self.dm.save_user(user_id, user)
        missions.pop(mission_id, None)
        self._save_missions(missions)
        return m