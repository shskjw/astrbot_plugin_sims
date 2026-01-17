from pathlib import Path
import uuid
import random
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..common.data_manager import DataManager
from ..common.cooldown import check_cooldown, set_cooldown
from .models import PoliceUser, Case, PoliceInfo, PoliceSkills, POLICE_RANKS

class PoliceLogic:
    def __init__(self, data_manager: Optional[DataManager] = None):
        self.dm = data_manager or DataManager()
        self.data_path = Path(self.dm.root) / 'data' / 'police'
        self.data_path.mkdir(parents=True, exist_ok=True)

    def _cases_file(self):
        return self.data_path / 'cases.json'

    def _police_file(self):
        return self.data_path / 'police_data.json'

    def _load_cases(self):
        p = self._cases_file()
        if not p.exists():
            return {}
        import json
        return json.loads(p.read_text(encoding='utf-8'))

    def _save_cases(self, data):
        import json
        p = self._cases_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _load_all_police(self):
        p = self._police_file()
        if not p.exists():
            return {}
        import json
        return json.loads(p.read_text(encoding='utf-8'))

    def _save_all_police(self, data):
        import json
        p = self._police_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _load_equipment_config(self):
        """加载装备配置"""
        p = Path(self.dm.root) / 'data' / 'police' / 'equipment.json'
        if not p.exists():
            return {}
        import json
        return json.loads(p.read_text(encoding='utf-8'))

    def _load_career_config(self):
        """加载职业配置"""
        p = Path(self.dm.root) / 'data' / 'police' / 'career.json'
        if not p.exists():
            return {}
        import json
        return json.loads(p.read_text(encoding='utf-8'))

    # ========== 基础功能 ==========

    def list_cases(self):
        return list(self._load_cases().values())

    def create_case(self, title: str, description: str, reward: int = 0, 
                    case_type: str = "普通", difficulty: str = "简单"):
        cases = self._load_cases()
        cid = str(uuid.uuid4())[:8]
        c = Case(
            id=cid, 
            title=title, 
            description=description, 
            reward=reward,
            type=case_type,
            difficulty=difficulty,
            created_at=datetime.utcnow().isoformat()
        )
        cases[cid] = c.dict()
        self._save_cases(cases)
        return c.dict()

    def accept_case(self, user_id: str, case_id: str):
        rem = check_cooldown(user_id, 'police', 'accept')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        cases = self._load_cases()
        c = cases.get(case_id)
        if not c:
            raise ValueError('案件不存在')
        if c.get('accepted_by'):
            raise ValueError('案件已被接取')
        
        # 保存到警察数据中
        police_data = self._load_all_police()
        user_police = police_data.get(user_id, {})
        user_police['current_case'] = c
        police_data[user_id] = user_police
        self._save_all_police(police_data)
        
        c['accepted_by'] = user_id
        cases[case_id] = c
        self._save_cases(cases)
        set_cooldown(user_id, 'police', 'accept', 5)
        return c

    def complete_case(self, user_id: str, case_id: str):
        cases = self._load_cases()
        c = cases.get(case_id)
        if not c:
            raise ValueError('案件不存在')
        if c.get('accepted_by') != user_id:
            raise ValueError('你未接取该案件')
        # reward user
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) + c.get('reward', 0)
        self.dm.save_user(user_id, user)
        
        # 更新警察数据
        police_data = self._load_all_police()
        user_police = police_data.get(user_id, {})
        info = user_police.get('info', {})
        info['cases_solved'] = info.get('cases_solved', 0) + 1
        info['experience'] = info.get('experience', 0) + c.get('reward', 0) // 10
        user_police['info'] = info
        user_police['current_case'] = None
        police_data[user_id] = user_police
        self._save_all_police(police_data)
        
        # mark resolved
        cases.pop(case_id, None)
        self._save_cases(cases)
        return c

    def get_user_info(self, user_id: str):
        police_data = self._load_all_police()
        return police_data.get(user_id, {})

    # ========== 加入警察 ==========

    def join_police(self, user_id: str, user_data: dict) -> dict:
        """加入警察队伍"""
        rem = check_cooldown(user_id, 'police', 'join')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        police_data = self._load_all_police()
        
        if user_id in police_data and police_data[user_id].get('info', {}).get('rank'):
            raise ValueError('你已经是警察了')
        
        # 初始化警察数据
        new_police = {
            'user_id': user_id,
            'name': user_data.get('name', '玩家'),
            'info': {
                'rank': '实习警员',
                'experience': 0,
                'cases_solved': 0,
                'patrol_hours': 0,
                'reputation': 50,
                'stamina': 100,
                'salary': POLICE_RANKS['实习警员']['salary'],
                'skills': {
                    'investigation': 1,
                    'combat': 1,
                    'leadership': 1,
                    'communication': 1
                }
            },
            'equipment': [],
            'current_case': None,
            'pending_cases': [],
            'joined_at': datetime.utcnow().isoformat()
        }
        
        police_data[user_id] = new_police
        self._save_all_police(police_data)
        
        # 更新用户数据
        user_data['job'] = '警察'
        self.dm.save_user(user_id, user_data)
        
        set_cooldown(user_id, 'police', 'join', 60)
        return new_police

    # ========== 巡逻系统 ==========

    def start_patrol(self, user_id: str) -> dict:
        """开始巡逻"""
        rem = check_cooldown(user_id, 'police', 'patrol')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        police_data = self._load_all_police()
        user_police = police_data.get(user_id)
        
        if not user_police:
            raise ValueError('你还不是警察')
        
        info = user_police.get('info', {})
        
        # 检查体力
        stamina = info.get('stamina', 100)
        if stamina < 20:
            raise ValueError('体力不足，需要休息')
        
        # 巡逻事件
        events = [
            {"type": "normal", "desc": "平静的巡逻", "exp": 10, "money": 100, "rep": 1},
            {"type": "minor", "desc": "处理小偷小摸", "exp": 20, "money": 200, "rep": 2},
            {"type": "dispute", "desc": "调解纠纷", "exp": 30, "money": 300, "rep": 3},
            {"type": "emergency", "desc": "紧急救助", "exp": 40, "money": 400, "rep": 4},
            {"type": "crime", "desc": "抓获罪犯", "exp": 50, "money": 500, "rep": 5}
        ]
        
        event = random.choice(events)
        
        # 装备加成
        equipment_bonus = sum(
            eq.get('stats', {}).get('patrolBonus', 0) 
            for eq in user_police.get('equipment', [])
        )
        
        # 计算奖励
        exp_gain = int(event['exp'] * (1 + equipment_bonus / 100))
        money_gain = int(event['money'] * (1 + equipment_bonus / 100))
        rep_gain = event['rep']
        
        # 更新数据
        info['experience'] = info.get('experience', 0) + exp_gain
        info['patrol_hours'] = info.get('patrol_hours', 0) + 1
        info['reputation'] = min(100, info.get('reputation', 50) + rep_gain)
        info['stamina'] = max(0, stamina - 20)
        
        # 随机提升技能
        skills = info.get('skills', {})
        skill_names = ['investigation', 'combat', 'leadership', 'communication']
        if random.random() < 0.3:
            skill = random.choice(skill_names)
            skills[skill] = min(10, skills.get(skill, 1) + 1)
        info['skills'] = skills
        
        # 检查升级
        self._check_rank_up(info)
        
        user_police['info'] = info
        police_data[user_id] = user_police
        self._save_all_police(police_data)
        
        # 发钱
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) + money_gain
        self.dm.save_user(user_id, user)
        
        set_cooldown(user_id, 'police', 'patrol', 30)
        
        return {
            'event': event,
            'exp_gain': exp_gain,
            'money_gain': money_gain,
            'rep_gain': rep_gain,
            'info': info
        }

    def _check_rank_up(self, info: dict):
        """检查是否可以晋升"""
        current_rank = info.get('rank', '实习警员')
        exp = info.get('experience', 0)
        
        ranks = list(POLICE_RANKS.keys())
        current_index = ranks.index(current_rank) if current_rank in ranks else 0
        
        # 自动晋升检查（只检查下一级）
        if current_index < len(ranks) - 1:
            next_rank = ranks[current_index + 1]
            if exp >= POLICE_RANKS[next_rank]['requiredExp']:
                # 不自动晋升，需要考核
                pass

    # ========== 装备商店 ==========

    def get_equipment_shop(self) -> dict:
        """获取装备商店列表"""
        config = self._load_equipment_config()
        return config

    def buy_equipment(self, user_id: str, equipment_name: str) -> dict:
        """购买装备"""
        rem = check_cooldown(user_id, 'police', 'buy')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        police_data = self._load_all_police()
        user_police = police_data.get(user_id)
        
        if not user_police:
            raise ValueError('你还不是警察')
        
        config = self._load_equipment_config()
        
        # 查找装备
        equipment = None
        category = ''
        for cat in ['weapons', 'armor', 'tools', 'special']:
            if cat in config and equipment_name in config[cat]:
                equipment = config[cat][equipment_name]
                category = cat
                break
        
        if not equipment:
            raise ValueError('未找到该装备')
        
        # 检查等级要求
        req = equipment.get('requirements', {})
        info = user_police.get('info', {})
        current_rank = info.get('rank', '实习警员')
        
        if req:
            required_level = req.get('level', 1)
            current_level = POLICE_RANKS.get(current_rank, {}).get('level', 1)
            if current_level < required_level:
                raise ValueError(f"需要达到{req.get('rank', '更高等级')}才能购买")
        
        # 检查金钱
        price = equipment.get('price', 0)
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < price:
            raise ValueError('金币不足')
        
        # 检查是否已有
        user_equipment = user_police.get('equipment', [])
        if any(eq.get('name') == equipment_name for eq in user_equipment):
            raise ValueError('你已经拥有该装备')
        
        # 购买
        user['money'] -= price
        self.dm.save_user(user_id, user)
        
        new_eq = {
            'name': equipment_name,
            'type': category,
            'durability': equipment.get('durability', 100),
            'stats': equipment.get('stats', {}),
            'maintenance_cost': equipment.get('maintenance', {}).get('cost', 100)
        }
        user_equipment.append(new_eq)
        user_police['equipment'] = user_equipment
        police_data[user_id] = user_police
        self._save_all_police(police_data)
        
        set_cooldown(user_id, 'police', 'buy', 10)
        
        return {
            'equipment': new_eq,
            'price': price,
            'remaining_money': user['money']
        }

    def maintain_equipment(self, user_id: str, equipment_name: str) -> dict:
        """维护装备"""
        rem = check_cooldown(user_id, 'police', 'maintain')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        police_data = self._load_all_police()
        user_police = police_data.get(user_id)
        
        if not user_police:
            raise ValueError('你还不是警察')
        
        user_equipment = user_police.get('equipment', [])
        eq = next((e for e in user_equipment if e.get('name') == equipment_name), None)
        
        if not eq:
            raise ValueError('你没有该装备')
        
        # 计算维护费用
        durability_loss = 100 - eq.get('durability', 100)
        base_cost = eq.get('maintenance_cost', 100)
        cost = int(base_cost * (durability_loss / 100 + 0.5))
        
        if cost <= 0:
            raise ValueError('装备状态良好，无需维护')
        
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < cost:
            raise ValueError('金币不足')
        
        # 维护
        user['money'] -= cost
        self.dm.save_user(user_id, user)
        
        old_durability = eq.get('durability', 100)
        eq['durability'] = 100
        
        police_data[user_id] = user_police
        self._save_all_police(police_data)
        
        set_cooldown(user_id, 'police', 'maintain', 30)
        
        return {
            'equipment': equipment_name,
            'cost': cost,
            'old_durability': old_durability,
            'new_durability': 100
        }

    # ========== 升职考核 ==========

    def promotion_exam(self, user_id: str) -> dict:
        """参加升职考核"""
        rem = check_cooldown(user_id, 'police', 'exam')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        police_data = self._load_all_police()
        user_police = police_data.get(user_id)
        
        if not user_police:
            raise ValueError('你还不是警察')
        
        info = user_police.get('info', {})
        current_rank = info.get('rank', '实习警员')
        
        ranks = list(POLICE_RANKS.keys())
        current_index = ranks.index(current_rank) if current_rank in ranks else 0
        
        if current_index >= len(ranks) - 1:
            raise ValueError('你已经是最高警衔')
        
        next_rank = ranks[current_index + 1]
        next_config = POLICE_RANKS[next_rank]
        
        # 检查经验要求
        if info.get('experience', 0) < next_config['requiredExp']:
            raise ValueError(f"经验不足，需要{next_config['requiredExp']}点经验")
        
        # 进行考核
        skills = info.get('skills', {})
        
        theory_base = random.randint(70, 100)
        physical_base = random.randint(70, 100)
        practical_base = random.randint(70, 100)
        
        theory_score = min(100, theory_base + skills.get('investigation', 1) * 2)
        physical_score = min(100, physical_base + skills.get('combat', 1) * 2)
        practical_score = min(100, practical_base + (skills.get('communication', 1) + skills.get('leadership', 1)) * 1.5)
        
        total_score = (theory_score + physical_score + practical_score) / 3
        passed = total_score >= 75
        
        if passed:
            info['rank'] = next_rank
            info['salary'] = next_config['salary']
            info['experience'] = info.get('experience', 0) + 500
            
            user = self.dm.load_user(user_id) or {}
            user['money'] = user.get('money', 0) + 5000
            self.dm.save_user(user_id, user)
        
        user_police['info'] = info
        police_data[user_id] = user_police
        self._save_all_police(police_data)
        
        set_cooldown(user_id, 'police', 'exam', 300)
        
        return {
            'current_rank': current_rank if not passed else None,
            'new_rank': next_rank if passed else None,
            'target_rank': next_rank,
            'theory_score': theory_score,
            'physical_score': physical_score,
            'practical_score': practical_score,
            'total_score': total_score,
            'passed': passed
        }

    # ========== 警员培训 ==========

    def police_training(self, user_id: str, skill_type: str) -> dict:
        """警员培训提升技能"""
        rem = check_cooldown(user_id, 'police', 'train')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        police_data = self._load_all_police()
        user_police = police_data.get(user_id)
        
        if not user_police:
            raise ValueError('你还不是警察')
        
        skill_mapping = {
            '调查': 'investigation',
            '战斗': 'combat',
            '领导': 'leadership',
            '沟通': 'communication'
        }
        
        skill_key = skill_mapping.get(skill_type)
        if not skill_key:
            raise ValueError(f"无效的培训类型，可选: {', '.join(skill_mapping.keys())}")
        
        info = user_police.get('info', {})
        skills = info.get('skills', {})
        current_level = skills.get(skill_key, 1)
        
        if current_level >= 10:
            raise ValueError('该技能已达到最高等级')
        
        # 检查体力
        stamina = info.get('stamina', 100)
        if stamina < 30:
            raise ValueError('体力不足')
        
        # 检查金钱
        train_cost = 1000
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < train_cost:
            raise ValueError('金币不足')
        
        # 培训成功率
        success_rate = 80 - (current_level * 5)
        success = random.randint(1, 100) <= success_rate
        
        # 扣费
        user['money'] -= train_cost
        info['stamina'] = stamina - 30
        self.dm.save_user(user_id, user)
        
        exp_gain = 0
        if success:
            skills[skill_key] = current_level + 1
            exp_gain = 100
            info['experience'] = info.get('experience', 0) + exp_gain
        
        info['skills'] = skills
        user_police['info'] = info
        police_data[user_id] = user_police
        self._save_all_police(police_data)
        
        set_cooldown(user_id, 'police', 'train', 60)
        
        return {
            'skill_type': skill_type,
            'old_level': current_level,
            'new_level': skills[skill_key],
            'success': success,
            'exp_gain': exp_gain,
            'cost': train_cost
        }

    # ========== 恢复体力 ==========

    def rest(self, user_id: str) -> dict:
        """休息恢复体力"""
        rem = check_cooldown(user_id, 'police', 'rest')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        police_data = self._load_all_police()
        user_police = police_data.get(user_id)
        
        if not user_police:
            raise ValueError('你还不是警察')
        
        info = user_police.get('info', {})
        old_stamina = info.get('stamina', 100)
        
        # 恢复30点体力
        info['stamina'] = min(100, old_stamina + 30)
        
        user_police['info'] = info
        police_data[user_id] = user_police
        self._save_all_police(police_data)
        
        set_cooldown(user_id, 'police', 'rest', 120)
        
        return {
            'old_stamina': old_stamina,
            'new_stamina': info['stamina']
        }

    # ========== 警察排行榜 ==========

    def get_police_ranking(self, rank_type: str = 'exp') -> List[dict]:
        """获取警察排行榜"""
        police_data = self._load_all_police()
        
        rankings = []
        for uid, data in police_data.items():
            info = data.get('info', {})
            rankings.append({
                'user_id': uid,
                'name': data.get('name', '未知'),
                'rank': info.get('rank', '实习警员'),
                'experience': info.get('experience', 0),
                'cases_solved': info.get('cases_solved', 0),
                'reputation': info.get('reputation', 50)
            })
        
        if rank_type == 'exp':
            rankings.sort(key=lambda x: x['experience'], reverse=True)
        elif rank_type == 'cases':
            rankings.sort(key=lambda x: x['cases_solved'], reverse=True)
        elif rank_type == 'reputation':
            rankings.sort(key=lambda x: x['reputation'], reverse=True)
        
        return rankings[:20]

    # ========== 处理案件 ==========

    def handle_case(self, user_id: str) -> dict:
        """处理当前案件"""
        rem = check_cooldown(user_id, 'police', 'case')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        police_data = self._load_all_police()
        user_police = police_data.get(user_id)
        
        if not user_police:
            raise ValueError('你还不是警察')
        
        current_case = user_police.get('current_case')
        if not current_case:
            raise ValueError('没有待处理的案件，请先接取案件')
        
        info = user_police.get('info', {})
        
        # 计算成功率
        difficulty_rates = {
            '简单': 90,
            '普通': 70,
            '困难': 50,
            '专家': 30
        }
        base_rate = difficulty_rates.get(current_case.get('difficulty', '简单'), 70)
        
        # 装备加成
        equipment_bonus = sum(
            eq.get('stats', {}).get('successRate', 0)
            for eq in user_police.get('equipment', [])
        )
        
        # 技能加成
        skills = info.get('skills', {})
        skill_bonus = skills.get('investigation', 1) * 2
        
        success_rate = min(95, base_rate + equipment_bonus + skill_bonus)
        success = random.randint(1, 100) <= success_rate
        
        # 计算奖励
        difficulty_multiplier = {
            '简单': 1,
            '普通': 1.5,
            '困难': 2,
            '专家': 3
        }.get(current_case.get('difficulty', '简单'), 1)
        
        base_reward = current_case.get('reward', 500)
        exp_gain = int(50 * difficulty_multiplier)
        money_gain = int(base_reward * difficulty_multiplier) if success else 0
        rep_change = 5 if success else -2
        
        if success:
            info['cases_solved'] = info.get('cases_solved', 0) + 1
            info['experience'] = info.get('experience', 0) + exp_gain
            info['reputation'] = min(100, info.get('reputation', 50) + rep_change)
            
            user = self.dm.load_user(user_id) or {}
            user['money'] = user.get('money', 0) + money_gain
            self.dm.save_user(user_id, user)
        else:
            info['reputation'] = max(0, info.get('reputation', 50) + rep_change)
        
        # 清除案件
        case_id = current_case.get('id')
        user_police['current_case'] = None
        user_police['info'] = info
        police_data[user_id] = user_police
        self._save_all_police(police_data)
        
        # 从案件列表移除
        cases = self._load_cases()
        cases.pop(case_id, None)
        self._save_cases(cases)
        
        set_cooldown(user_id, 'police', 'case', 60)
        
        return {
            'case': current_case,
            'success': success,
            'exp_gain': exp_gain if success else 0,
            'money_gain': money_gain,
            'rep_change': rep_change,
            'info': info
        }

    # ========== 生成随机案件 ==========

    def generate_random_case(self) -> dict:
        """生成随机案件"""
        case_types = [
            {"type": "盗窃", "titles": ["商店盗窃案", "入室盗窃案", "扒窃案件"], "reward": 300},
            {"type": "暴力", "titles": ["斗殴事件", "持械伤人", "聚众闹事"], "reward": 500},
            {"type": "诈骗", "titles": ["电信诈骗", "网络诈骗", "投资骗局"], "reward": 400},
            {"type": "普通", "titles": ["交通事故", "邻里纠纷", "走失人口"], "reward": 200}
        ]
        
        difficulties = ["简单", "普通", "困难", "专家"]
        diff_weights = [40, 35, 20, 5]
        
        case_type = random.choice(case_types)
        difficulty = random.choices(difficulties, weights=diff_weights)[0]
        title = random.choice(case_type['titles'])
        
        return self.create_case(
            title=title,
            description=f"一起{case_type['type']}类型的案件，难度: {difficulty}",
            reward=case_type['reward'],
            case_type=case_type['type'],
            difficulty=difficulty
        )
